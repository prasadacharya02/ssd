# ============================================================
# ENTROPY - Defense Tamper Guard
# monitoring/defense_guard.py
#
# Ransomware kills the victim's defenses before or during
# encryption: Shadow Copies, backup services, and backup stores.
# Detecting that behavior is a near-certain incident signal:
#
#   1. Protected-path deletion — DELETED events under the backup
#      store or quarantine directory.
#   2. Defense-tamper command lines — a running process whose
#      command line matches known defense-kill signatures
#      (vssadmin delete shadows, shadowcopy deletion, wbadmin,
#      service stops, registry deletion).
#
# collect_threat_flags() is the single entry point used by both
# the live pipeline (EventPipeline._merge_event) and the benchmark
# harness, so both exercise identical logic.
# ============================================================

import os
import time
from threading import Lock

import psutil

import config
from blockchain.fingerprint_exchange import get_exchange
from response.ransom_note import detect_ransom_note

# (signature, description) — matched as lowercase substrings of the
# joined process command line.
TAMPER_CMDLINE_SIGNATURES = (
    ("vssadmin", "vssadmin (Shadow Copy management)"),
    ("shadowcopy delete", "Shadow Copy deletion (wmic)"),
    ("wbadmin", "wbadmin (Windows Backup admin)"),
    ("net stop", "service stop (net stop)"),
    ("sc stop", "service stop (sc)"),
    ("sc delete", "service removal (sc delete)"),
    ("reg delete", "registry deletion (reg delete)"),
)

_scan_cache = {"t": 0.0, "hits": None}
_scan_lock = Lock()


def is_protected_path(path: str,
                      protected_roots: tuple | None = None) -> bool:
    """True if *path* lies inside a protected store (backup or
    quarantine), or inside one of *protected_roots* (benchmark use)."""
    if not path:
        return False
    target = os.path.abspath(path)
    roots = tuple(protected_roots) if protected_roots else (
        config.BACKUP_DIR, config.QUARANTINE_DIR
    )
    for root in roots:
        root_abs = os.path.abspath(root)
        if target == root_abs or target.startswith(root_abs + os.sep):
            return True
    return False


def scan_process_cmdlines(max_age_seconds: float = 2.0) -> list:
    """Scan running processes for defense-tamper command lines.

    Results are cached for a short TTL: this is called per threat
    event, and a full psutil sweep should not run more than ~0.5x/s.
    """
    now = time.time()
    with _scan_lock:
        age = now - _scan_cache["t"]
        # A negative age (clock rewound / synthetic test time) invalidates
        # the cache instead of treating it as "just scanned".
        if _scan_cache["hits"] is not None and 0 <= age < max_age_seconds:
            return list(_scan_cache["hits"])

    hits = []
    our_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] == our_pid:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if not cmdline:
                continue
            low = cmdline.lower()
            for signature, description in TAMPER_CMDLINE_SIGNATURES:
                if signature in low:
                    hits.append({
                        "pid": proc.info["pid"],
                        "name": proc.info.get("name") or "",
                        "cmdline": cmdline[:300],
                        "signature": description,
                    })
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue

    with _scan_lock:
        _scan_cache["t"] = now
        _scan_cache["hits"] = hits
    return list(hits)


def collect_threat_flags(event: dict,
                         protected_roots: tuple | None = None,
                         exchange=None) -> dict:
    """Compute the hard-confirmation flags for one file event.

    Returns a dict with: ransom_note, ransom_note_evidence,
    defense_tamper, defense_tamper_evidence, known_threat,
    known_threat_evidence, known_threat_confirmed. The caller merges
    it into the event before the decision engine sees it.

    ``exchange`` defaults to the node's shared store; the benchmark
    and the multi-node simulation inject isolated instances so they
    never read or write the real registry.
    """
    flags = {
        "ransom_note": False,
        "ransom_note_evidence": [],
        "defense_tamper": False,
        "defense_tamper_evidence": [],
        "known_threat": False,
        "known_threat_evidence": "",
        "known_threat_confirmed": False,
    }
    file_path = event.get("file_path") or ""
    event_type = (event.get("event_type") or "").upper()

    # 1. Ransom note: created or modified small text files.
    if event_type in ("CREATED", "MODIFIED") and file_path:
        try:
            is_note, evidence = detect_ransom_note(file_path)
        except Exception:
            is_note, evidence = False, []
        if is_note:
            flags["ransom_note"] = True
            flags["ransom_note_evidence"] = list(evidence)

    # 2. Protected-store tamper: deletion inside the backup/quarantine
    # stores means the attacker is destroying recovery capability.
    if event_type == "DELETED" and file_path and \
            is_protected_path(file_path, protected_roots) and \
            not os.path.exists(file_path):
        # (A path that still exists was replaced, not destroyed — e.g.
        # the store's own atomic rewrite; that is not tampering.)
        flags["defense_tamper"] = True
        flags["defense_tamper_evidence"].append(
            f"deletion of protected path: "
            f"{os.path.basename(file_path)}"
        )

    # 3. Escalation scan: once something else already looks like a
    # threat, check for a defense-kill command line in the wild.
    threaty = (
        flags["ransom_note"]
        or flags["defense_tamper"]
        or float(event.get("threat_score") or 0.0) >= 40.0
    )
    if threaty and not flags["defense_tamper"]:
        try:
            hits = scan_process_cmdlines()
        except Exception:
            hits = []
        if hits:
            flags["defense_tamper"] = True
            flags["defense_tamper_evidence"].extend(
                f"process {h['pid']} ({h['name']}): {h['signature']}"
                for h in hits[:3]
            )

    # 4. Federated exchange: has any node already contained this exact
    # fingerprint as a confirmed threat? A single node's sighting is
    # corroboration only; >= EXCHANGE_CONFIRM_THRESHOLD *independent*
    # sources confirm the fingerprint as a known threat.
    fingerprint = event.get("file_hash") or ""
    if fingerprint:
        # An injected exchange is an explicit opt-in; the canonical
        # store is gated by config.EXCHANGE_ENABLED.
        if exchange is None and not config.EXCHANGE_ENABLED:
            store = None
        else:
            store = exchange if exchange is not None else get_exchange()
        try:
            rec = store.lookup(fingerprint) if store is not None else None
        except Exception:
            rec = None
        if rec:
            sources = rec.get("sources") or []
            flags["known_threat"] = True
            flags["known_threat_evidence"] = (
                f"contained by {len(sources)} node(s) "
                f"[{', '.join(sources)}], "
                f"{rec.get('sightings', 0)} sighting(s) on record"
            )
            if len(sources) >= config.EXCHANGE_CONFIRM_THRESHOLD:
                flags["known_threat_confirmed"] = True

    return flags
