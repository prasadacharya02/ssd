import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import config
from response.backup_manager import BackupManager
from response.forensic_report import (generate_report, list_reports,
                                      load_report)


def _clean_bytes(seed: int = 1) -> bytes:
    return f"clean document content {seed}".encode() * 50


def _dirty_bytes() -> bytes:
    return os.urandom(65536)


class BackupManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.backup_dir = str(self.tmp / "backup_storage")
        self.backup = BackupManager(backup_dir=self.backup_dir)
        self.target = self.tmp / "victim" / "document.txt"
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, content: bytes):
        self.target.write_bytes(content)

    def test_capture_creates_verified_version(self):
        self._write(_clean_bytes())
        result = self.backup.capture(
            str(self.target),
            event={"entropy_overall": 4.1, "event_type": "CREATED"},
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["captured"])
        self.assertTrue(result["clean"])

        manifest = json.loads(
            (Path(self.backup_dir) / "manifest.json").read_text()
        )
        entry = manifest[str(self.target)][0]
        blob = Path(self.backup_dir) / "versions" / entry["sha256"]
        self.assertTrue(blob.is_file())

        import hashlib
        self.assertEqual(
            entry["sha256"],
            hashlib.sha256(_clean_bytes()).hexdigest(),
        )
        self.assertEqual(entry["entropy"], 4.1)

    def test_capture_labels_high_entropy_versions_unclean(self):
        self._write(_dirty_bytes())
        result = self.backup.capture(
            str(self.target),
            event={"entropy_overall": 8.0, "event_type": "MODIFIED"},
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["clean"])
        self.assertIsNone(
            self.backup.find_restore_candidate(str(self.target))
        )

    def test_restore_recovers_clean_content(self):
        clean = _clean_bytes()
        self._write(clean)
        with mock.patch.object(config, "DRY_RUN", False):
            self.backup.capture(
                str(self.target),
                event={"entropy_overall": 4.1, "event_type": "CREATED"},
            )
            self._write(_dirty_bytes())  # "attack"
            result = self.backup.restore(
                str(self.target),
                event={"timestamp": datetime.now().isoformat()},
            )
        self.assertTrue(result["success"])
        self.assertTrue(result["restored"])
        self.assertEqual(self.target.read_bytes(), clean)

    def test_restore_selects_pre_attack_version(self):
        self._write(_clean_bytes(seed=1))
        with mock.patch.object(config, "DRY_RUN", False):
            self.backup.capture(
                str(self.target),
                event={"entropy_overall": 4.1,
                       "event_type": "startup_baseline"},
            )
            # A benign edit after the baseline is also restorable.
            before_attack = (datetime.now() + timedelta(seconds=1)).isoformat()
            self._write(_clean_bytes(seed=2))
            self.backup.capture(
                str(self.target),
                event={"entropy_overall": 4.2,
                       "event_type": "MODIFIED",
                       "timestamp": before_attack},
            )
            # The attack happens strictly after the last clean write.
            self._write(_dirty_bytes())
            self.backup.capture(
                str(self.target),
                event={"entropy_overall": 8.0,
                       "event_type": "MODIFIED",
                       "timestamp": datetime.now().isoformat()},
            )
            result = self.backup.restore(
                str(self.target),
                event={"timestamp": datetime.now().isoformat()},
            )
        self.assertTrue(result["success"])
        self.assertTrue(result["restored"])
        self.assertEqual(self.target.read_bytes(), _clean_bytes(seed=2))

    def test_restore_refused_without_clean_backup(self):
        self._write(_dirty_bytes())
        self.backup.capture(
            str(self.target),
            event={"entropy_overall": 8.0, "event_type": "startup_baseline"},
        )
        encrypted = self.target.read_bytes()
        with mock.patch.object(config, "DRY_RUN", False):
            result = self.backup.restore(
                str(self.target),
                event={"timestamp": datetime.now().isoformat()},
            )
        self.assertFalse(result["success"])
        self.assertIn("No clean backup", result["message"])
        self.assertEqual(self.target.read_bytes(), encrypted)

    def test_dry_run_restore_leaves_file_untouched(self):
        self._write(_clean_bytes())
        with mock.patch.object(config, "DRY_RUN", True):
            self.backup.capture(
                str(self.target),
                event={"entropy_overall": 4.1, "event_type": "CREATED"},
            )
        self._write(_dirty_bytes())
        encrypted = self.target.read_bytes()
        with mock.patch.object(config, "DRY_RUN", True):
            result = self.backup.restore(
                str(self.target),
                event={"timestamp": datetime.now().isoformat()},
            )
        self.assertTrue(result["success"])
        self.assertFalse(result["restored"])
        self.assertIn("Dry-run", result["message"])
        self.assertEqual(self.target.read_bytes(), encrypted)

    def test_version_cap_evicts_oldest(self):
        backup = BackupManager(backup_dir=self.backup_dir, max_versions=3)
        for i in range(5):
            self._write(_clean_bytes(seed=i))
            backup.capture(
                str(self.target),
                event={"entropy_overall": 4.0, "event_type": "MODIFIED"},
            )
        manifest = json.loads(
            (Path(self.backup_dir) / "manifest.json").read_text()
        )
        versions = manifest[str(self.target)]
        self.assertEqual(len(versions), 3)
        self.assertEqual([v["version"] for v in versions], [1, 2, 3])
        # The two oldest blobs must have been evicted from the store.
        blobs = list((Path(self.backup_dir) / "versions").iterdir())
        self.assertEqual(len(blobs), len({v["sha256"] for v in versions}))

    def test_snapshot_directory_captures_baseline(self):
        self._write(_clean_bytes())
        (self.tmp / "victim" / "other.txt").write_text("hello world")
        captured = self.backup.snapshot_directory(str(self.tmp / "victim"))
        self.assertEqual(captured, 2)
        stats = self.backup.stats()
        self.assertEqual(stats["files_protected"], 2)
        self.assertEqual(stats["files_restorable"], 2)

    def test_transfer_moves_version_history(self):
        self._write(_clean_bytes(seed=7))
        self.backup.capture(
            str(self.target),
            event={"entropy_overall": 4.1, "event_type": "MODIFIED"},
        )
        new_path = self.tmp / "victim" / "document.locked"
        moved = self.backup.transfer(str(self.target), str(new_path))
        self.assertTrue(moved)
        # Old path no longer has restorable versions; new path does.
        self.assertIsNone(self.backup.find_restore_candidate(str(self.target)))
        candidate = self.backup.find_restore_candidate(str(new_path))
        self.assertIsNotNone(candidate)

    def test_rename_recovery_finds_clean_version(self):
        """Production rename sequence: encrypt+rename, transfer the
        pre-rename history, capture the encrypted state, then restore
        must bring the pre-attack bytes back at the NEW path."""
        clean = _clean_bytes(seed=3)
        self._write(clean)
        self.backup.capture(
            str(self.target),
            event={"entropy_overall": 4.1, "event_type": "MODIFIED"},
        )
        # The attacker encrypts in place and disguises with a rename.
        new_path = self.tmp / "victim" / "document.locked"
        self.target.write_bytes(_dirty_bytes())
        os.replace(str(self.target), str(new_path))
        # Pipeline order: transfer history, then capture the new state.
        self.assertTrue(self.backup.transfer(str(self.target), str(new_path)))
        self.backup.capture(
            str(new_path),
            event={"entropy_overall": 8.0, "event_type": "RENAMED"},
        )
        with mock.patch.object(config, "DRY_RUN", False):
            result = self.backup.restore(str(new_path))
        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["restored"])
        self.assertEqual(new_path.read_bytes(), clean)


class ForensicReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.reports_dir = str(Path(self._tmp.name) / "reports")

    def tearDown(self):
        self._tmp.cleanup()

    def test_report_is_written_and_loadable(self):
        event = {
            "event_id": "evt123",
            "event_type": "MODIFIED",
            "file_path": "/victim/Documents/notes.txt",
            "file_extension": ".txt",
            "entropy_overall": 8.0,
            "entropy_delta": 4.5,
            "prev_entropy": 3.5,
            "reason": "Large entropy change",
            "file_hash": "ab" * 32,
            "process": {
                "pid": 4242,
                "name": "python",
                "identity_verified": False,
                "attribution_source": "recent_process_guess",
            },
        }
        decision = {
            "engine": "rules",
            "action": 3,
            "action_name": "TERMINATED+QUARANTINED",
            "confidence": 1.0,
            "explanation": "Rule-based detector",
        }
        response_record = {
            "requested_action": 3,
            "outcome": "QUARANTINED+RESTORED",
            "dry_run": False,
            "terminate": "TERMINATE_REFUSED",
            "quarantine": "QUARANTINED",
            "restore": "RESTORED",
            "blockchain_reference": "ab" * 32,
        }

        path = generate_report(event, decision, response_record,
                               reports_dir=self.reports_dir)
        self.assertTrue(path)
        self.assertTrue(os.path.isfile(path))

        data = json.loads(Path(path).read_text())
        self.assertEqual(data["incident"]["file_path"],
                         "/victim/Documents/notes.txt")
        self.assertEqual(data["entropy_evidence"]["entropy_overall"], 8.0)
        self.assertEqual(data["decision"]["action"], 3)
        self.assertEqual(data["response"]["outcome"], "QUARANTINED+RESTORED")
        self.assertFalse(
            data["incident"]["process"]["identity_verified"]
        )

        listed = list_reports(reports_dir=self.reports_dir)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["report_id"], data["report_id"])

        loaded = load_report(os.path.basename(path),
                             reports_dir=self.reports_dir)
        self.assertEqual(loaded["report_id"], data["report_id"])

    def test_load_report_rejects_path_traversal(self):
        self.assertIsNone(load_report("../secret.json",
                                      reports_dir=self.reports_dir))
        self.assertIsNone(load_report("nope.txt",
                                      reports_dir=self.reports_dir))
        self.assertIsNone(load_report("a/b.json",
                                      reports_dir=self.reports_dir))


class _FakeLedger:
    def __init__(self):
        self.events = []

    def log_event(self, event):
        self.events.append(event)


class PipelineRecoveryWiringTests(unittest.TestCase):
    """execute_response must run restore + forensic report end to end."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.backup = BackupManager(backup_dir=str(self.tmp / "backup"))
        self.quarantine_dir = self.tmp / "quarantine"
        self.reports_dir = self.tmp / "reports"
        self.target = self.tmp / "victim" / "document.txt"
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = _FakeLedger()
        # These tests exercise recovery, not the federated exchange:
        # keep confirmed-threat registration out of the real store.
        self._exchange_disabled = mock.patch.object(
            config, "EXCHANGE_ENABLED", False
        )
        self._exchange_disabled.start()

    def tearDown(self):
        self._exchange_disabled.stop()
        self._tmp.cleanup()

    def _event(self, entropy: float, delta: float = 0.0,
               timestamp: str | None = None) -> dict:
        return {
            "event_id": "evt-wiring",
            "timestamp": timestamp or datetime.now().isoformat(),
            "file_path": str(self.target),
            "event_type": "MODIFIED",
            "file_extension": ".txt",
            "entropy_overall": entropy,
            "entropy_delta": delta,
            "threat_score": 75.0,
            "file_hash": "cd" * 32,
            "process": {
                "pid": 0,
                "name": "unknown",
                "identity_verified": False,
                "attribution_source": "none",
            },
        }

    def _db(self):
        from storage.database import init_db
        return init_db(str(self.tmp / "events.db"))

    def test_dry_run_response_quarantines_simulated_and_restores_simulated(
            self):
        self.target.write_bytes(_clean_bytes())
        self.backup.capture(
            str(self.target),
            event={"entropy_overall": 4.1, "event_type": "CREATED"},
        )
        encrypted = _dirty_bytes()
        self.target.write_bytes(encrypted)  # attack
        self.backup.capture(
            str(self.target),
            event=self._event(8.0),
        )

        conn = self._db()
        with mock.patch.object(config, "DRY_RUN", True), \
             mock.patch.object(config, "QUARANTINE_DIR",
                               str(self.quarantine_dir)), \
             mock.patch.object(config, "REPORTS_DIR", str(self.reports_dir)):
            outcome = self._run_response(conn)

        self.assertIn("DRY_RUN_QUARANTINE", outcome)
        self.assertIn("DRY_RUN_RESTORE", outcome)
        self.assertTrue(self.target.exists())  # file left in place
        self.assertEqual(self.target.read_bytes(), encrypted)
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])

        row = conn.execute(
            "SELECT restore_result, outcome, dry_run FROM events"
        ).fetchone()
        self.assertEqual(row["restore_result"], "DRY_RUN_RESTORE")
        self.assertEqual(row["dry_run"], 1)

        reports = list(self.reports_dir.glob("forensic_*.json"))
        self.assertEqual(len(reports), 1)
        conn.close()

    def _run_response(self, conn) -> str:
        from monitoring.pipeline_runner import execute_response
        return execute_response(
            config.ACTION_TERMINATE_QUARANTINE,
            self._event(8.0, delta=4.5),
            self.ledger, conn,
            decision={
                "engine": "rules",
                "action": config.ACTION_TERMINATE_QUARANTINE,
                "action_name": "TERMINATED+QUARANTINED",
                "confidence": 1.0,
                "explanation": "test",
            },
            backup=self.backup,
        )

    def test_live_response_quarantines_and_restores_clean_copy(self):
        clean = _clean_bytes()
        encrypted = _dirty_bytes()
        self.target.write_bytes(clean)
        self.backup.capture(
            str(self.target),
            event={"entropy_overall": 4.1, "event_type": "CREATED"},
        )
        self.target.write_bytes(encrypted)  # attack
        self.backup.capture(
            str(self.target),
            event=self._event(8.0),
        )

        conn = self._db()
        with mock.patch.object(config, "DRY_RUN", False), \
             mock.patch.object(config, "QUARANTINE_DIR",
                               str(self.quarantine_dir)), \
             mock.patch.object(config, "REPORTS_DIR", str(self.reports_dir)):
            outcome = self._run_response(conn)

        self.assertIn("QUARANTINED", outcome)
        self.assertIn("RESTORED", outcome)
        # The victim path holds the clean bytes again...
        self.assertEqual(self.target.read_bytes(), clean)
        # ...and the encrypted copy sits in quarantine.
        quarantined = [p for p in self.quarantine_dir.iterdir()
                       if not p.name.endswith(".meta.json")]
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), encrypted)

        row = conn.execute(
            "SELECT restore_result FROM events"
        ).fetchone()
        self.assertEqual(row["restore_result"], "RESTORED")

        self.assertTrue(list(self.reports_dir.glob("forensic_*.json")))
        self.assertTrue(self.ledger.events)
        conn.close()


if __name__ == "__main__":
    unittest.main()
