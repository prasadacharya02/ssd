# ============================================================
# ENTROPY - Forensic Report Generator
# response/forensic_report.py
#
# Produces one durable, machine-readable incident report per
# threat: the entropy evidence, the AI decision, the response
# actions (requested vs actual), the recovery outcome, and the
# ledger reference. Stored under reports/ so auditors (and the
# dashboard) can trace an incident end to end without database
# access.
# ============================================================

import json
import os
from datetime import datetime

import config


def _safe_name(file_path: str) -> str:
    name = os.path.basename(file_path) or "unknown"
    return "".join(c for c in name if c.isalnum() or c in "-_.")[:64] or "unknown"


def generate_report(event: dict, decision: dict, response_record: dict,
                    reports_dir: str | None = None) -> str | None:
    """Write a forensic report for one incident.

    Returns the report path, or None if nothing could be written.
    """
    event = event or {}
    decision = decision or {}
    response_record = response_record or {}

    directory = reports_dir or config.REPORTS_DIR
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return None

    timestamp = datetime.now()
    incident_id = event.get("event_id") or timestamp.strftime("%Y%m%d%H%M%S%f")
    incident_id = "".join(c for c in str(incident_id) if c.isalnum())[:32] or \
        timestamp.strftime("%Y%m%d%H%M%S%f")

    report = {
        "schema_version": 1,
        "report_id": f"INC-{timestamp.strftime('%Y%m%d-%H%M%S')}-{incident_id}",
        "generated_at": timestamp.isoformat(),

        # ── What happened ────────────────────────────────────
        "incident": {
            "event_id": event.get("event_id", ""),
            "event_type": event.get("event_type", ""),
            "file_path": event.get("file_path", ""),
            "file_extension": event.get("file_extension", ""),
            "file_size": event.get("file_size"),
            "process": {
                "pid": (event.get("process") or {}).get("pid"),
                "name": (event.get("process") or {}).get("name", "unknown"),
                "identity_verified": (event.get("process") or {}).get(
                    "identity_verified", False
                ),
                "attribution_source": (event.get("process") or {}).get(
                    "attribution_source", "none"
                ),
            },
            "events_per_sec": event.get("events_per_sec"),
        },

        # ── The fingerprint (why it was flagged) ─────────────
        "entropy_evidence": {
            "entropy_overall": event.get("entropy_overall"),
            "entropy_delta": event.get("entropy_delta"),
            "prev_entropy": event.get("prev_entropy"),
            "section_entropy": {
                "start": event.get("entropy_start"),
                "middle": event.get("entropy_middle"),
                "end": event.get("entropy_end"),
            },
            "normal_range": [
                event.get("normal_range_min"),
                event.get("normal_range_max"),
            ],
            "threshold": config.ENTROPY_THRESHOLD,
            "reason": event.get("reason", ""),
            "indicators": event.get("indicators", []),
            "file_hash": event.get("file_hash", ""),
        },

        # ── The decision ─────────────────────────────────────
        "decision": {
            "engine": decision.get("engine", "unknown"),
            "action": decision.get("action"),
            "action_name": decision.get("action_name", ""),
            "confidence": decision.get("confidence"),
            "explanation": decision.get("explanation", ""),
            "q_values": decision.get("q_values"),
        },

        # ── The response (requested vs actual) ───────────────
        "response": {
            "requested_action": response_record.get("requested_action"),
            "outcome": response_record.get("outcome"),
            "dry_run": response_record.get("dry_run", bool(config.DRY_RUN)),
            "process_terminate": response_record.get("terminate"),
            "quarantine": response_record.get("quarantine"),
            "restore": response_record.get("restore"),
        },

        # ── Audit trail ──────────────────────────────────────
        "audit": {
            "blockchain_reference": response_record.get("blockchain_reference"),
            "database_event_id": response_record.get("database_event_id"),
        },
    }

    path = os.path.join(
        directory,
        f"forensic_{timestamp.strftime('%Y%m%d_%H%M%S')}_{incident_id}_"
        f"{_safe_name(event.get('file_path', ''))}.json",
    )
    try:
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
        os.replace(temporary, path)
        return path
    except OSError:
        return None


def list_reports(reports_dir: str | None = None) -> list:
    """List forensic reports, newest first."""
    directory = reports_dir or config.REPORTS_DIR
    entries = []
    if not os.path.isdir(directory):
        return entries
    for name in os.listdir(directory):
        if not (name.startswith("forensic_") and name.endswith(".json")):
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        try:
            stat = os.stat(path)
            data = {}
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        entries.append({
            "name": name,
            "report_id": data.get("report_id", ""),
            "generated_at": data.get("generated_at", ""),
            "file_path": data.get("incident", {}).get("file_path", ""),
            "action_name": data.get("decision", {}).get("action_name", ""),
            "outcome": data.get("response", {}).get("outcome", ""),
            "size_bytes": stat.st_size,
        })
    entries.sort(key=lambda e: e["generated_at"], reverse=True)
    return entries


def load_report(name: str, reports_dir: str | None = None) -> dict | None:
    """Load one report by file name (path traversal is not possible)."""
    directory = reports_dir or config.REPORTS_DIR
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    if not (name.startswith("forensic_") and name.endswith(".json")):
        return None
    path = os.path.join(directory, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None
