"""ENTROPY attacker operator console service (port 8001).

The console is the offensive half of the lab: it launches the simulated
ransomware process against the victim fixture estate, streams that process's
output, and reports what happened — including the moment the ENTROPY response
pipeline terminates it.

Two front ends are supported:

* ``attacker-ui/`` — React + Tailwind console built into
  ``attacker_server/static/console/`` (the default once built).
* ``attacker_server/templates/attacker.html`` — the legacy single-file
  console, still served as a fallback on a fresh clone.

Both drive the same REST API and are subject to the same control authorization.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
VICTIM_DIR = os.path.join(ROOT_DIR, "victim_server")
USER_FILES = os.path.join(VICTIM_DIR, "user_files")

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
LEGACY_HTML_PATH = os.path.join(TEMPLATES_DIR, "attacker.html")

# Built React console (attacker-ui/ -> attacker_server/static/console/).
CONSOLE_DIR = os.path.join(BASE_DIR, "static", "console")
CONSOLE_INDEX = os.path.join(CONSOLE_DIR, "index.html")
CONSOLE_URL_PREFIX = "/static/console/"

# Compatibility alias: older tooling and tests refer to HTML_PATH.
HTML_PATH = LEGACY_HTML_PATH

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, VICTIM_DIR)

import config
import ransomware_engines as engines

from catalog import FAMILIES as CATALOG_FAMILIES, LOCK_EXTENSIONS

try:
    from create_fake_files import restore_all_files
except Exception:
    restore_all_files = None


# ============================================================
# Malware process manager
# ============================================================
# The attack runs as a SEPARATE OS process (python -m
# attacker_server.ransomware_engines <family>). This mirrors real
# malware — a rogue process on the machine — so the defender's
# response (kill the PID that has the file open + quarantine the
# file) acts on a genuine, verifiable process instead of a thread
# inside the attacker console.
#
#   operator stop  -> SIGINT -> clean exit (code 0)
#   defender kill  -> SIGTERM -> exit code 42 (KILLED_BY_DEFENDER)
#
# The streamed process output becomes the operator console log.
# ============================================================

_proc_lock = threading.Lock()
_proc = None            # subprocess.Popen | None
_proc_family = None     # selected family id
_stream = deque(maxlen=400)
_control_path = os.path.join(ROOT_DIR, "attacker_control.json")

_KILLED_EXIT = 42

_SCAN_RE = re.compile(
    r"scan complete:\s*(\d+)\s*targets,\s*(\d+)\s*skipped"
)
_HIT_RE = re.compile(r"encrypted\s+(\d+)/(\d+)")
_NOTE_RE = re.compile(r"Note dropped:")
_BYTES_RE = re.compile(r"\((\d+)\s*bytes\)")
_FINISHED_RE = re.compile(r"attack finished:\s*(\d+)/(\d+)")
_DEFENDER_RE = re.compile(r"TERMINATED BY DEFENSE")
_OPERATOR_STOP_RE = re.compile(r"stopped by operator")

# Ransom-note filenames come from the shared catalog so the console, the
# victim explorer and the SOC all agree on what an artifact looks like.
NOTE_MARKERS = tuple(
    sorted(
        {
            marker
            for family in CATALOG_FAMILIES
            for marker in family.get("note_markers", ())
        }
    )
)

# Order matters: the first match wins.
_LEVEL_PATTERNS = (
    (re.compile(r"TERMINATED BY DEFENSE", re.IGNORECASE), "critical"),
    (re.compile(r"\b(error|failed|failure|traceback|exception|missing)\b", re.IGNORECASE), "error"),
    (re.compile(r"\b(warn|paused|stopped by operator|skip)\b", re.IGNORECASE), "warn"),
)


def _classify(message: str) -> str:
    """Map one process output line to a console level."""
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.search(message):
            return level
    return "info"


def _write_control(payload):
    """Merge *payload* into the operator control file."""
    current = {}
    try:
        with open(_control_path, encoding="utf-8") as fh:
            current = json.load(fh)
    except (OSError, ValueError):
        pass
    current.update(payload)
    try:
        with open(_control_path, "w", encoding="utf-8") as fh:
            json.dump(current, fh)
    except OSError:
        pass


def _stream_reader(proc):
    """Copy the child's stdout into the in-memory console log.

    Each line is timestamped on arrival and classified, so the console can
    render levels and ordering without re-parsing strings in the browser.

    When the stream closes (the child exited — killed by the defender
    or finished), reap the child here. Without this the child sits as
    a zombie until something polls the console, and any *other*
    process waiting on that PID (the defender's ProcessTerminator is
    not the child's parent) times out on a process that is already
    dead.
    """
    try:
        for line in proc.stdout:
            text = line.rstrip("\n")
            if not text:
                continue
            entry = {
                "time": time.strftime("%H:%M:%S"),
                "at": time.time(),
                "msg": text,
                "level": _classify(text),
            }
            with _proc_lock:
                _stream.append(entry)
    except (OSError, ValueError):
        pass
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            pass


def _spawn(family_id):
    """Start the attack as a child process. Returns (ok, message)."""
    global _proc, _proc_family
    with _proc_lock:
        if _proc is not None and _proc.poll() is None:
            return False, f"{_proc_family} already running"
        _stream.clear()
        _write_control({"factor": 1.0, "paused": False})
        command = [
            sys.executable,
            "-m",
            "attacker_server.ransomware_engines",
            family_id,
            "--control",
            _control_path,
        ]
        _proc = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        _proc_family = family_id
    threading.Thread(
        target=_stream_reader, args=(_proc,), daemon=True
    ).start()
    return True, "ok"


def _read_control_or_default():
    try:
        with open(_control_path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _derive_phase(alive, messages, control, returncode):
    """Single source of truth for the phase shown on the console."""
    joined = "\n".join(messages)

    if alive:
        if control.get("paused"):
            return "PAUSED"
        return "ENCRYPTING" if "scan complete:" in joined else "SCANNING"

    if _DEFENDER_RE.search(joined) or returncode == _KILLED_EXIT:
        return "KILLED_BY_DEFENDER"
    if not messages:
        return "IDLE"
    if _FINISHED_RE.search(joined):
        return "COMPLETED"
    if _OPERATOR_STOP_RE.search(joined):
        return "STOPPED"
    return "STOPPED"


def _child_state():
    """Summarize the running (or last) attack process for the console."""
    with _proc_lock:
        proc = _proc
        family = _proc_family
        lines = list(_stream)

    control = _read_control_or_default()

    if proc is None:
        # Stable contract: the console always receives the same keys, idle or
        # running, so it never has to guess at an undefined counter.
        return {
            "active": False,
            "family": None,
            "phase": "IDLE",
            "paused": False,
            "speed_factor": float(control.get("factor", 1.0) or 1.0),
            "progress": 0,
            "targets": 0,
            "files_hit": 0,
            "files_skipped": 0,
            "notes_dropped": 0,
            "bytes_encrypted": 0,
            "files_per_second": 0.0,
            "elapsed_seconds": 0.0,
            "started_at": None,
            "finished_at": None,
            "pid": None,
            "exit_code": None,
            "returncode": None,
            "defender_killed": False,
            "log": lines,
        }

    alive = proc.poll() is None
    messages = [entry.get("msg", "") for entry in lines]

    targets = skipped = hit = total = notes = 0
    bytes_encrypted = 0

    for message in messages:
        match = _SCAN_RE.search(message)
        if match:
            targets, skipped = int(match.group(1)), int(match.group(2))
            continue
        match = _HIT_RE.search(message)
        if match:
            hit = max(hit, int(match.group(1)))
            total = max(total, int(match.group(2)))
            continue
        if _NOTE_RE.search(message):
            notes += 1
            continue
        match = _BYTES_RE.search(message)
        if match and "encrypting" in message:
            bytes_encrypted += int(match.group(1))

    phase = _derive_phase(alive, messages, control, proc.returncode)

    if lines:
        first_at = lines[0].get("at") or time.time()
        last_at = lines[-1].get("at") or first_at
        finished_at = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(last_at)
        )
    else:
        first_at = last_at = None
        finished_at = None

    if first_at is None:
        elapsed = 0.0
    elif alive:
        elapsed = max(0.0, time.time() - first_at)
    else:
        elapsed = max(0.0, last_at - first_at)

    staged = targets or total
    rate = round(hit / elapsed, 3) if elapsed > 0.25 else 0.0

    defender_killed = phase == "KILLED_BY_DEFENDER"

    return {
        "active": alive,
        "family": family,
        "phase": phase,
        "paused": bool(alive and control.get("paused")),
        "speed_factor": float(control.get("factor", 1.0) or 1.0),
        "progress": round(min(100, hit / max(staged, 1) * 100), 1) if staged else 0,
        "targets": targets,
        "files_hit": hit,
        "files_skipped": skipped,
        "notes_dropped": notes,
        "bytes_encrypted": bytes_encrypted,
        "files_per_second": rate,
        "elapsed_seconds": round(elapsed, 1),
        "started_at": (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(first_at))
            if first_at
            else None
        ),
        "finished_at": None if alive else finished_at,
        "pid": proc.pid if alive else None,
        "exit_code": None if alive else proc.returncode,
        "returncode": proc.returncode,
        "defender_killed": defender_killed,
        "log": lines,
    }


def _stop_child(operator: bool):
    """Stop the child: SIGINT for the operator, wait for exit."""
    with _proc_lock:
        proc = _proc
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.send_signal(signal.SIGINT if operator else signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return False
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return True


# ============================================================
# Victim estate snapshots
# ============================================================


def _count_store_files(directory, skip_suffixes=()):
    """Count regular files in a store directory (one level is enough)."""
    total = 0
    if not os.path.isdir(directory):
        return 0
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if any(filename.endswith(suffix) for suffix in skip_suffixes):
                continue
            total += 1
        if root.count(os.sep) - directory.count(os.sep) > 2:
            continue
    return total


def estate_snapshot():
    """Read-only description of the victim fixture estate.

    One walk produces everything the operator console shows: file and byte
    totals, per-folder counts, extension mix, and how many files carry
    defender or attacker artifacts.
    """
    snapshot = {
        "exists": os.path.isdir(USER_FILES),
        "total": 0,
        "bytes": 0,
        "attackable": 0,
        "locked": 0,
        "notes": 0,
        "folders": [],
        "extensions": [],
        "quarantine_evidence": _count_store_files(
            config.QUARANTINE_DIR, skip_suffixes=(".meta.json",)
        ),
        "backed_up": _count_store_files(
            os.path.join(config.BACKUP_DIR, "versions")
        ),
    }

    if not snapshot["exists"]:
        return snapshot

    folders = {}
    extensions = {}

    for directory, _, filenames in os.walk(USER_FILES):
        relative = os.path.relpath(directory, USER_FILES)
        folder_name = "(root)" if relative == "." else relative.replace(os.sep, "/")
        bucket = folders.setdefault(folder_name, {"name": folder_name, "files": 0, "bytes": 0})

        for filename in filenames:
            path = os.path.join(directory, filename)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0

            extension = os.path.splitext(filename)[1].lower() or "(none)"
            lowercase_name = filename.lower()

            snapshot["total"] += 1
            snapshot["bytes"] += size
            bucket["files"] += 1
            bucket["bytes"] += size
            extensions[extension] = extensions.get(extension, 0) + 1

            if extension in LOCK_EXTENSIONS:
                snapshot["locked"] += 1
            if any(marker in lowercase_name for marker in NOTE_MARKERS):
                snapshot["notes"] += 1

    snapshot["attackable"] = max(
        0, snapshot["total"] - snapshot["locked"] - snapshot["notes"]
    )
    snapshot["folders"] = sorted(folders.values(), key=lambda item: item["name"])
    snapshot["extensions"] = sorted(
        ({"ext": ext, "files": count} for ext, count in extensions.items()),
        key=lambda item: (-item["files"], item["ext"]),
    )
    return snapshot


def victim_snapshot():
    """Compact neutrality-preserving counters (used by /api/stats)."""
    estate = estate_snapshot()
    return {
        "exists": estate["exists"],
        "total": estate["total"],
        "locked": estate["locked"],
        "notes": estate["notes"],
        "bytes": estate["bytes"],
    }


# ============================================================
# HTTP helpers
# ============================================================

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


def read_json(handler):
    content_length = int(
        handler.headers.get("Content-Length") or 0
    )

    if content_length <= 0:
        return {}

    raw = handler.rfile.read(content_length)

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _send_bytes(handler, body, content_type, status=200, cache="no-store", extra=None):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache)
    for header, value in (extra or {}).items():
        handler.send_header(header, value)
    handler.end_headers()
    handler.wfile.write(body)


def send_json(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    _send_bytes(handler, body, "application/json; charset=utf-8", status=status)


def send_text(
    handler,
    text,
    content_type="text/plain; charset=utf-8",
    filename="campaign.log",
):
    body = text.encode("utf-8")
    _send_bytes(
        handler,
        body,
        content_type,
        extra={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _runtime_links(handler):
    """Public URLs for the sibling services, resolved per request."""
    host_header = handler.headers.get("Host", "127.0.0.1:8001")
    host = host_header.split(":", 1)[0]
    scheme = "https" if handler.headers.get("X-Forwarded-Proto") == "https" else "http"

    return {
        "__VICTIM_URL__": config.PUBLIC_VICTIM_URL or f"{scheme}://{host}:8002",
        "__DASHBOARD_URL__": config.PUBLIC_DASHBOARD_URL or f"{scheme}://{host}:5000",
        "__ATTACKER_URL__": config.PUBLIC_ATTACKER_URL or f"{scheme}://{host}:8001",
        "__CONTROL_TOKEN__": getattr(config, "CONTROL_TOKEN", "") or "",
    }


def _render_html(html, handler):
    for placeholder, value in _runtime_links(handler).items():
        html = html.replace(placeholder, value)
    return html


def console_index_available():
    return os.path.isfile(CONSOLE_INDEX)


def send_console_html(handler):
    """Serve the built React console with runtime values injected."""
    with open(CONSOLE_INDEX, "r", encoding="utf-8") as file:
        html = _render_html(file.read(), handler)

    _send_bytes(handler, html.encode("utf-8"), "text/html; charset=utf-8")


def send_html(handler):
    """Legacy single-file console (fallback when the bundle is absent)."""
    with open(LEGACY_HTML_PATH, "r", encoding="utf-8") as file:
        html = _render_html(file.read(), handler)

    _send_bytes(handler, html.encode("utf-8"), "text/html; charset=utf-8")


def send_index(handler):
    """Serve whichever console build exists, preferring the React bundle."""
    if console_index_available():
        send_console_html(handler)
    else:
        send_html(handler)


def _console_asset_path(path):
    """Map a /static/console/ URL onto a file inside the bundle directory.

    Returns ``None`` for anything that escapes the bundle root.
    """
    relative = unquote(path[len(CONSOLE_URL_PREFIX):])
    if not relative or relative.endswith("/"):
        return None

    root = os.path.realpath(CONSOLE_DIR)
    candidate = os.path.realpath(os.path.join(root, relative))

    if candidate != root and not candidate.startswith(root + os.sep):
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate


def send_console_asset(handler, path):
    if path.rstrip("/") == CONSOLE_URL_PREFIX.rstrip("/") or path.endswith(
        CONSOLE_URL_PREFIX + "index.html"
    ):
        send_console_html(handler)
        return

    candidate = _console_asset_path(path)
    if candidate is None:
        handler.send_error(404, "not found")
        return

    extension = os.path.splitext(candidate)[1].lower()
    content_type = _CONTENT_TYPES.get(extension, "application/octet-stream")

    with open(candidate, "rb") as file:
        body = file.read()

    # Hashed asset filenames are safe to cache; the console HTML is not.
    cache = "public, max-age=3600"
    _send_bytes(handler, body, content_type, cache=cache)


def control_authorized(handler):
    """
    Localhost is allowed by default.

    If ENTROPY_CONTROL_TOKEN is configured,
    remote control requires:
    Authorization: Bearer <token>
    """
    configured_token = config.CONTROL_TOKEN

    if configured_token:
        supplied = handler.headers.get(
            "Authorization",
            "",
        )

        expected = f"Bearer {configured_token}"

        return hmac.compare_digest(
            supplied,
            expected,
        )

    try:
        address = ipaddress.ip_address(
            handler.client_address[0]
        )
        return address.is_loopback
    except ValueError:
        return False


# Compatibility alias expected by tests/test_control_security.py
_control_authorized = control_authorized


def send_forbidden(handler):
    send_json(
        handler,
        {
            "ok": False,
            "error": (
                "control route requires local access "
                "or a valid bearer token"
            ),
        },
        status=403,
    )


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format_string, *args):
        sys.stderr.write(
            "[attacker] "
            + (format_string % args)
            + "\n"
        )

    def do_GET(self):
        path = urlparse(self.path).path

        if path.startswith(CONSOLE_URL_PREFIX):
            send_console_asset(self, path)
            return

        if path in {
            "/",
            "/index.html",
            "/attacker.html",
        }:
            send_index(self)
            return

        if path == "/api/families":
            send_json(self, engines.list_families())
            return

        if path == "/api/stats":
            stats = _child_state()
            stats["victim"] = victim_snapshot()
            send_json(self, stats)
            return

        if path == "/api/targets":
            send_json(self, estate_snapshot())
            return

        if path == "/api/log":
            state = _child_state()
            header = [
                "# ENTROPY attacker console export",
                f"# family : {state.get('family') or '-'}",
                f"# phase  : {state.get('phase')}",
                f"# exit   : {state.get('exit_code')}",
                f"# targets: {state.get('targets')}  encrypted: {state.get('files_hit')}",
                "",
            ]
            lines = [
                f"{entry.get('time', '--:--:--')}  {entry.get('msg', '')}"
                for entry in state.get("log", [])
            ]
            send_text(self, "\n".join(header + lines) + "\n")
            return

        if path == "/healthz":
            send_json(self, {"ok": True, "phase": _child_state()["phase"]})
            return

        self.send_error(404, "not found")

    def do_HEAD(self):
        """Only expose metadata for routes this service actually serves.

        SimpleHTTPRequestHandler's default implementation walks the process
        working directory, which would leak file metadata for the whole repo.
        """
        path = urlparse(self.path).path

        if path.startswith(CONSOLE_URL_PREFIX):
            candidate = _console_asset_path(path)
            if candidate is None and not path.endswith(
                CONSOLE_URL_PREFIX + "index.html"
            ):
                self.send_error(404, "not found")
                return
            extension = os.path.splitext(candidate or CONSOLE_INDEX)[1].lower()
            _send_bytes(
                self,
                b"",
                _CONTENT_TYPES.get(extension, "application/octet-stream"),
                cache="no-store",
            )
            return

        if path in {"/", "/index.html", "/attacker.html", "/api/stats", "/api/families", "/api/targets"}:
            _send_bytes(self, b"", "text/html; charset=utf-8", cache="no-store")
            return

        self.send_error(404, "not found")

    def do_POST(self):
        path = urlparse(self.path).path

        protected_routes = {
            "/api/launch",
            "/api/stop",
            "/api/pause",
            "/api/resume",
            "/api/speed",
            "/api/reset",
        }

        if (
            path in protected_routes
            and not control_authorized(self)
        ):
            send_forbidden(self)
            return

        data = read_json(self)

        if path == "/api/launch":
            family = (
                data.get("family") or ""
            ).strip().lower()

            if family not in engines.FAMILIES:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": "unknown family",
                    },
                    status=400,
                )
                return

            snapshot = victim_snapshot()

            if (
                not snapshot["exists"]
                or snapshot["total"] == 0
            ):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "victim folder is empty — "
                            "hit RESET first"
                        ),
                    },
                    status=400,
                )
                return

            current = _child_state()

            if current.get("active"):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            f"{current.get('family')} "
                            "already running"
                        ),
                    },
                    status=409,
                )
                return

            ok, message = _spawn(family)

            if not ok:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": message,
                    },
                    status=500,
                )
                return

            send_json(
                self,
                {
                    "ok": True,
                    "family": family,
                    "pid": _child_state()["pid"],
                    "stats": _child_state(),
                },
            )
            return

        if path == "/api/stop":
            # Operator stop = SIGINT (clean exit), distinct from the
            # defender's SIGTERM kill so the console can tell them apart.
            stopped = _stop_child(operator=True)
            send_json(
                self,
                {
                    "ok": True,
                    "stopped": bool(stopped),
                },
            )
            return

        if path == "/api/pause":
            state = _child_state()
            ok = bool(state.get("active"))
            if ok:
                _write_control({"paused": True})

            send_json(
                self,
                {
                    "ok": ok,
                    "paused": ok,
                },
            )
            return

        if path == "/api/resume":
            state = _child_state()
            ok = bool(state.get("active"))
            if ok:
                _write_control({"paused": False})

            send_json(
                self,
                {
                    "ok": ok,
                    "paused": False,
                },
            )
            return

        if path == "/api/speed":
            try:
                factor = float(
                    data.get("factor", 1.0)
                )

                speed = min(5.0, max(0.1, factor))
                _write_control({"factor": speed})

                send_json(
                    self,
                    {
                        "ok": True,
                        "speed_factor": speed,
                    },
                )
            except (TypeError, ValueError):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": "invalid speed",
                    },
                    status=400,
                )
            return

        if path == "/api/reset":
            if _child_state().get("active"):
                _stop_child(operator=True)

            if restore_all_files is None:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "create_fake_files.py "
                            "is unavailable"
                        ),
                    },
                    status=500,
                )
                return

            try:
                restore_all_files()

                send_json(
                    self,
                    {
                        "ok": True,
                        "victim": victim_snapshot(),
                        "estate": estate_snapshot(),
                    },
                )
            except Exception as exc:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": str(exc),
                    },
                    status=500,
                )
            return

        self.send_error(404, "not found")


if __name__ == "__main__":
    print("=" * 60)
    print("  ATTACKER OPERATOR CONSOLE")
    print("  http://0.0.0.0:8001")
    print(
        "  front end: "
        + ("attacker-ui bundle (static/console)" if console_index_available()
           else "legacy templates/attacker.html (run `npm run build` in attacker-ui/)")
    )
    print("=" * 60)

    server = ThreadingHTTPServer(
        ("0.0.0.0", 8001),
        Handler,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAttacker server stopped")
        server.shutdown()
        server.server_close()
