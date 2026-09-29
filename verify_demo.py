# verify_demo.py
# ============================================================
# ENTROPY - Required End-to-End Verification (autonomous)
# ============================================================
# Automates the project's REQUIRED END-TO-END TEST against a
# RUNNING lab (started with `python lab.py`):
#
#   PREPARATION   services online, victim tree hashed (SHA-256),
#                 backup store present, blockchain mode reported
#   ATTACK        safe ransomware simulator launched (WannaCry default)
#   DEFENSE       waits for containment, then verifies:
#                   - malicious process terminated (exit 42)
#                   - no ciphertext left in the victim tree
#                   - every file hash-matches its pre-attack state
#                   - quarantine + restore events in the SOC feed
#                   - blockchain/ledger records written
#                   - forensic reports generated
#   TIMELINE      T0..T7 with detection/containment/recovery latencies,
#                 measured from INDEPENDENT sources (verifier clock +
#                 attacker telemetry + event DB + pre-attack manifest) -
#                 the defender never grades its own homework.
#
# Exit code 0 = every critical check passed. 1 = failure, printed in
# the FAILED COMPONENT / ROOT CAUSE / FIX format.
#
# Usage:
#   python3 lab.py                 # terminal 1 (the lab must be running)
#   python3 verify_demo.py         # terminal 2 (defaults: WannaCry)
#   python3 verify_demo.py --family lockbit5 --settle 10
# ============================================================

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
VICTIM_DIR = ROOT / "victim_server" / "user_files"
BACKUP_MANIFEST = ROOT / "backup_storage" / "manifest.json"
REPORTS_DIR = ROOT / "reports"

ATTACK_LEFTOVER_SUFFIXES = (".wncry", ".locked", ".encrypted", ".crypt")


# ── tiny JSON-over-HTTP helpers (stdlib only) ───────────────

def _request(method: str, url: str, *, token: str = "",
             payload: dict | None = None, timeout: float = 10.0):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    return json.loads(raw) if raw.strip() else {}


def _get(url: str, **kw):
    return _request("GET", url, **kw)


def _post(url: str, payload: dict, **kw):
    return _request("POST", url, payload=payload, **kw)


# ── checks bookkeeping ──────────────────────────────────────

class Verdict:
    def __init__(self):
        self.rows = []           # (level, component, expected, actual, fix)
        self.critical_failed = 0

    def check(self, component: str, ok: bool, expected: str,
              actual: str, fix: str = "", *, critical: bool = True):
        level = "PASS" if ok else ("FAIL" if critical else "WARN")
        if not ok and critical:
            self.critical_failed += 1
        self.rows.append((level, component, expected, actual, fix))
        return ok

    def print_report(self):
        print()
        print("=" * 78)
        print("  VERIFICATION CHECKS")
        print("=" * 78)
        for level, comp, expected, actual, fix in self.rows:
            print(f"  [{level:4}] {comp}")
            print(f"         expected : {expected}")
            print(f"         actual   : {actual}")
            if level != "PASS" and fix:
                print(f"         fix      : {fix}")
        print("-" * 78)
        if self.critical_failed == 0:
            print("  VERDICT: PASS - the complete defensive lifecycle works.")
        else:
            print(f"  VERDICT: FAIL - {self.critical_failed} critical "
                  f"component(s) failed. Project is NOT demo-ready.")
        print("=" * 78)


# ── victim tree hashing ─────────────────────────────────────

def snapshot_tree(root: Path) -> dict:
    """sha256 + size for every file under *root* (relative paths)."""
    manifest = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(root))] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
    return manifest


def attack_leftovers(root: Path) -> list:
    return sorted(
        str(p.relative_to(root)) for p in root.rglob("*")
        if p.is_file() and p.name.lower().endswith(ATTACK_LEFTOVER_SUFFIXES)
    )


def _parse_iso(value: str):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the required ENTROPY end-to-end verification.")
    parser.add_argument("--family", default="wannacry",
                        help="ransomware family to launch (default wannacry)")
    parser.add_argument("--dashboard", default="http://127.0.0.1:5000")
    parser.add_argument("--attacker", default="http://127.0.0.1:8001")
    parser.add_argument("--token",
                        default=os.environ.get("ENTROPY_CONTROL_TOKEN",
                                               "entropy-lab"))
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="max seconds to wait for containment")
    parser.add_argument("--settle", type=float, default=8.0,
                        help="seconds to wait after containment so sweep, "
                             "post-kill verification and ledger writes land")
    parser.add_argument("--no-reset", action="store_true",
                        help="do not reset the victim estate before attacking")
    args = parser.parse_args(argv)

    v = Verdict()
    print("=" * 78)
    print("  ENTROPY - REQUIRED END-TO-END VERIFICATION")
    print("  DETECT > KILL > QUARANTINE > RESTORE > VERIFY > LOG > SOC")
    print("=" * 78)

    # ────────────────────────────────────────────────────────
    # PHASE 0 - SERVICES
    # ────────────────────────────────────────────────────────
    print("\n[PHASE 0] Checking services ...")
    try:
        pipe = _get(f"{args.dashboard}/api/pipeline")
        pipeline_ok = True
    except Exception as exc:
        pipe = {}
        pipeline_ok = False
        v.check("SOC dashboard reachable", False, "HTTP 200 on /api/pipeline",
                str(exc), "start the lab: python lab.py")
    if pipeline_ok:
        v.check("SOC dashboard reachable", True, "HTTP 200", "HTTP 200")
        v.check("Detection pipeline ONLINE", bool(pipe.get("online")),
                "online=true", f"online={pipe.get('online')}",
                "start the lab: python lab.py")
        v.check("Victim folder watched", bool(pipe.get("watching_victim")),
                "watching_victim=true",
                f"watching_victim={pipe.get('watching_victim')}",
                "check ENTROPY_WATCH_FOLDERS / .env")
        v.check("Live mode (not dry-run)", pipe.get("dry_run") is False,
                "dry_run=false", f"dry_run={pipe.get('dry_run')}",
                "unset ENTROPY_DRY_RUN or run lab.py without --dry-run")
    try:
        bc = _get(f"{args.dashboard}/api/blockchain/status")
        bc_mode = bc.get("mode", "unknown")
        print(f"  blockchain adapter: mode={bc_mode} "
              f"(fallback = labeled local ledger; honest, not a real chain)")
    except Exception:
        bc_mode = "unreachable"
        print("  blockchain adapter: status endpoint unreachable")
    try:
        pre_attack_stats = _get(f"{args.attacker}/api/stats")
        v.check("Attacker console reachable", True, "HTTP 200", "HTTP 200")
        v.check("No attack already running",
                not pre_attack_stats.get("active"), "active=false",
                f"phase={pre_attack_stats.get('phase')}",
                "wait for the current run to finish")
    except Exception as exc:
        v.check("Attacker console reachable", False, "HTTP 200 on /api/stats",
                str(exc), "start the lab: python lab.py")
        return _finish(v)

    ledger_before = _get(f"{args.dashboard}/api/stats").get("blockchain_tx", 0)

    # ────────────────────────────────────────────────────────
    # PHASE 1 - PREPARATION (reset, baseline hashes, backup)
    # ────────────────────────────────────────────────────────
    print("\n[PHASE 1] Preparation: clean victim + pre-attack manifest ...")
    if not args.no_reset:
        try:
            _post(f"{args.attacker}/api/reset", {}, token=args.token)
            print(f"  victim estate reset; settling {args.settle:.0f}s so the "
                  f"pipeline can re-baseline")
            time.sleep(args.settle)
        except Exception as exc:
            v.check("Victim reset", False, "ok=true", str(exc),
                    "check ENTROPY_CONTROL_TOKEN matches lab services")
            return _finish(v)

    leftovers_pre = attack_leftovers(VICTIM_DIR)
    if not v.check("Victim tree clean before attack", not leftovers_pre,
                   "no *.WNCRY / *.locked files",
                   f"leftovers: {leftovers_pre[:3]}",
                   "reset the estate (attacker console RESET)"):
        return _finish(v)

    manifest = snapshot_tree(VICTIM_DIR)
    v.check("Victim files present", len(manifest) > 0, ">= 1 file",
            f"{len(manifest)} files hashed (SHA-256 manifest captured)")
    print(f"  pre-attack manifest : {len(manifest)} file(s), SHA-256 recorded")

    backup_note = ""
    versions = 0
    if BACKUP_MANIFEST.exists():
        try:
            backlog = json.loads(BACKUP_MANIFEST.read_text())
            versions = sum(len(vers) for vers in backlog.values())
        except Exception:
            backlog = {}
    v.check(
        "Protected backup store populated", versions >= len(manifest),
        f">= {len(manifest)} clean version(s) "
        f"(backup_storage/, OUTSIDE the folder the simulator may touch)",
        f"{versions} version(s) on record",
        "restart the pipeline so the startup baseline is captured",
        critical=False)
    print(f"  backup store        : {BACKUP_MANIFEST.parent} "
          f"({versions} versioned clean copies, attacker sandbox excludes it)")

    reports_before = {p.name for p in REPORTS_DIR.glob("forensic_*.json")} \
        if REPORTS_DIR.is_dir() else set()

    # ────────────────────────────────────────────────────────
    # PHASE 2 - ATTACK
    # ────────────────────────────────────────────────────────
    print(f"\n[PHASE 2] Launching safe ransomware simulation "
          f"({args.family}) ...")
    t0_wall = time.time()
    try:
        launch = _post(f"{args.attacker}/api/launch",
                       {"family": args.family}, token=args.token)
    except Exception as exc:
        v.check("Attack launch", False, "ok=true", str(exc),
                "check family name and control token")
        return _finish(v)
    if not v.check("Attack launch", bool(launch.get("ok")), "ok=true",
                   json.dumps(launch)[:160],
                   "attacker console reports the error"):
        return _finish(v)
    pid = (launch.get("stats") or {}).get("pid")
    print(f"  simulator running   : pid={pid}")

    # ────────────────────────────────────────────────────────
    # PHASE 3 - WAIT FOR CONTAINMENT
    # ────────────────────────────────────────────────────────
    print("\n[PHASE 3] Waiting for the defense to react ...")
    final = {}
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            final = _get(f"{args.attacker}/api/stats")
        except Exception:
            continue
        if not final.get("active"):
            break
    phase = final.get("phase", "?")
    rc = final.get("returncode")
    files_hit = final.get("files_hit", 0)
    elapsed = final.get("elapsed_seconds", 0.0)
    print(f"  outcome             : phase={phase} | exit={rc} | "
          f"files encrypted before kill={files_hit} | "
          f"attacker ran {elapsed:.1f}s")

    v.check("Malicious process CONTAINED by defender",
            phase == "KILLED_BY_DEFENDER" and rc == 42,
            "phase=KILLED_BY_DEFENDER, exit code 42 (defender SIGTERM)",
            f"phase={phase}, exit={rc}",
            "if the attack completed, detection never fired - check "
            "pipeline logs and ENTROPY_WATCH_FOLDERS")
    print(f"  settling {args.settle:.0f}s for sweep, restore and ledger ...")
    time.sleep(args.settle)

    # ────────────────────────────────────────────────────────
    # PHASE 4 - POST-ATTACK VERIFICATION
    # ────────────────────────────────────────────────────────
    print("\n[PHASE 4] Verifying estate, logs and ledger ...")

    # 4a. no ciphertext left
    leftovers = attack_leftovers(VICTIM_DIR)
    v.check("No encrypted files left behind", not leftovers,
            "0 files with attack extensions in victim tree",
            f"{len(leftovers)} leftover(s): {leftovers[:3]}")

    # 4b. hash verification against the pre-attack manifest
    post = snapshot_tree(VICTIM_DIR)
    matches = sum(1 for rel, meta in manifest.items()
                  if post.get(rel, {}).get("sha256") == meta["sha256"])
    missing = [rel for rel in manifest if rel not in post]
    differs = [rel for rel in manifest
               if rel in post and post[rel]["sha256"] != manifest[rel]["sha256"]]
    extra = [rel for rel in post if rel not in manifest]
    v.check("All files byte-identical after recovery",
            not missing and not differs and not extra,
            f"{len(manifest)}/{len(manifest)} SHA-256 match, 0 missing/extra",
            f"{matches}/{len(manifest)} match | missing={missing[:2]} "
            f"differs={differs[:2]} extra={extra[:2]}",
            "investigate restore: reports/ and backup manifest")
    t7_wall = time.time()   # integrity verification finished

    # 4c. SOC event feed: timeline reconstruction
    events = []
    try:
        events = _get(f"{args.dashboard}/api/events?limit=400")
    except Exception:
        pass
    from datetime import datetime, timedelta
    t0_local = datetime.now() - timedelta(seconds=time.time() - t0_wall)
    rows = []
    for row in events:
        ts = _parse_iso(row.get("timestamp"))
        if ts and ts >= t0_local - timedelta(seconds=2):
            rows.append((ts, row))
    rows.sort(key=lambda item: item[0])

    def _first(pred):
        for ts, row in rows:
            if pred(str(row.get("outcome", ""))):
                return ts, row
        return None, None

    t1, _ = (rows[0] if rows else (None, None))
    alert_ts, _ = _first(lambda o: "ALERT" in o)
    contain_ts, contain_row = _first(lambda o: "QUARANTINE" in o.upper())
    restore_ts_list = [ts for ts, row in rows if "RESTORED" in
                       str(row.get("outcome", ""))]
    t2 = alert_ts or contain_ts
    t6 = restore_ts_list[-1] if restore_ts_list else None
    quarantine_rows = [r for _ts, r in rows
                       if "QUARANTINE" in str(r.get("outcome", "")).upper()]

    v.check("Detection events in SOC feed", t2 is not None,
            ">= 1 ALERT/THREAT event for this attack",
            f"{len(rows)} event(s) recorded")
    v.check("Quarantine action recorded", bool(quarantine_rows),
            ">= 1 QUARANTINED event", f"{len(quarantine_rows)} event(s)")
    v.check("Restore action recorded", bool(restore_ts_list),
            ">= 1 +RESTORED outcome", f"{len(restore_ts_list)} restore(s)")

    # 4d. ledger writing
    ledger_after = _get(f"{args.dashboard}/api/stats").get("blockchain_tx", 0)
    v.check("Threat fingerprint recorded in ledger",
            ledger_after > ledger_before,
            f"> {ledger_before} records (mode: {bc_mode})",
            f"{ledger_after} records")

    # 4e. forensic reports
    reports_after = {p.name for p in REPORTS_DIR.glob("forensic_*.json")} \
        if REPORTS_DIR.is_dir() else set()
    new_reports = sorted(reports_after - reports_before)
    v.check("Forensic incident report written", bool(new_reports),
            ">= 1 new reports/forensic_*.json",
            f"{len(new_reports)} new report(s)")

    # ────────────────────────────────────────────────────────
    # TIMELINE + BEFORE/DURING/AFTER BOARD
    # ────────────────────────────────────────────────────────
    def _s(delta_pair):
        a, b = delta_pair
        if a is None or b is None:
            return "n/a"
        return f"{(b - a).total_seconds():.2f}s"

    print()
    print("=" * 78)
    print("  ATTACK TIMELINE (independent measurement, wall clock)")
    print("=" * 78)
    wall = lambda t: time.strftime("%H:%M:%S", time.localtime(t))
    print(f"  T0 attack launched           {wall(t0_wall)}")
    print(f"  T1 first event detected      "
          f"{t1.strftime('%H:%M:%S') if t1 else 'n/a'}")
    print(f"  T2 anomaly detected/alerted  "
          f"{t2.strftime('%H:%M:%S') if t2 else 'n/a'}")
    print(f"  T4 process terminated        "
          f"{(wall(t0_wall + elapsed)) if phase else 'n/a'} "
          f"(attacker exit at {elapsed:.1f}s of runtime)")
    print(f"  T5 quarantine recorded       "
          f"{contain_ts.strftime('%H:%M:%S') if contain_ts else 'n/a'}")
    print(f"  T6 last restore completed    "
          f"{t6.strftime('%H:%M:%S') if t6 else 'n/a'}")
    print(f"  T7 integrity verified        {wall(t7_wall)}")
    print("  " + "-" * 74)
    print(f"  detection latency   (T2-T1)  {_s((t1, t2))}")
    print(f"  containment latency (T5-T2)  {_s((t2, contain_ts))}")
    print(f"  recovery latency    (T6-T5)  {_s((contain_ts, t6))}")
    print(f"  attacker wall time (kill)    {elapsed:.2f}s "
          f"after {files_hit} file(s)")

    print()
    print("=" * 78)
    print("  BEFORE / DURING / AFTER (demo board)")
    print("=" * 78)
    print(f"  BEFORE : files={len(manifest)} healthy | backup={'yes' if versions else 'check'} "
          f"| pipeline={'online' if pipe.get('online') else 'OFFLINE'} "
          f"| soc=online | blockchain={bc_mode}")
    print(f"  DURING : simulator={args.family} pid={pid} | files hit={files_hit} "
          f"| detected+contained={phase}")
    print(f"  AFTER  : process={'terminated' if rc == 42 else 'RUNNING?'} "
          f"| leftovers={len(leftovers)} | quarantined={len(quarantine_rows)} "
          f"| restored={len(restore_ts_list)} | hash match="
          f"{matches}/{len(manifest)} | ledger +{ledger_after - ledger_before} "
          f"| reports +{len(new_reports)}")
    if new_reports:
        print(f"  newest forensic report: {new_reports[-1]}")
    return _finish(v)


def _finish(v: Verdict) -> int:
    v.print_report()
    return 0 if v.critical_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
