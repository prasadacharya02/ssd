"""Ransom-note and defense-tamper hard-confirmation signals."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from monitoring.defense_guard import (collect_threat_flags,
                                      is_protected_path,
                                      scan_process_cmdlines)
from monitoring.pipeline_runner import make_decision
from monitoring.watchdog_monitor import FileMonitor
from response.ransom_note import detect_ransom_note


NOTE_TEXT = (
    "Your files have been encrypted with AES-256.\n"
    "To recover your files, pay 0.5 BTC to the wallet address below.\n"
    "You have 72 hours to pay.\n"
)

CLEAN_DOC = (
    "Quarterly planning notes. The budget committee approved the "
    "proposal. We will review the backup schedule next quarter and "
    "rotate the encryption keys in Q4.\n"
) * 10


class RansomNoteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, content) -> str:
        path = self.tmp / name
        path.write_bytes(
            content.encode() if isinstance(content, str) else content
        )
        return str(path)

    def test_known_note_filenames_detected(self):
        for name in ("Restore-My-Files.txt", "please_read_me.txt",
                     "MAZE-README.txt", "HOW-TO-DECRYPT-FILES.txt",
                     "@Please_Read_Me@.txt", "recover-your-files.html"):
            with self.subTest(name=name):
                path = self._write(name, "whatever")
                is_note, evidence = detect_ransom_note(path)
                self.assertTrue(is_note, name)
                self.assertTrue(evidence)

    def test_ordinary_readme_is_not_a_note(self):
        path = self._write("README.txt", "Project documentation.")
        self.assertFalse(detect_ransom_note(path)[0])

    def test_note_content_detected_by_strong_marker(self):
        path = self._write("notes_2024.txt", NOTE_TEXT)
        is_note, evidence = detect_ransom_note(path)
        self.assertTrue(is_note)
        self.assertTrue(evidence)

    def test_clean_document_is_not_a_note(self):
        """A document that mentions 'backup' and 'keys' must stay quiet:
        weak markers alone (fewer than two specific phrases) don't fire."""
        path = self._write("planning.txt", CLEAN_DOC)
        self.assertFalse(detect_ransom_note(path)[0])

    def test_binary_file_not_scanned(self):
        path = self._write("data.bin", b"\x00\x01\x02" * 100)
        self.assertFalse(detect_ransom_note(path)[0])


class DefenseGuardTests(unittest.TestCase):
    def setUp(self):
        # Reset the shared cmdline-scan cache between tests.
        import monitoring.defense_guard as guard
        with guard._scan_lock:
            guard._scan_cache.update({"t": 0.0, "hits": None})

    def test_protected_path_detection(self):
        with mock.patch.object(config, "BACKUP_DIR", "/data/backup_storage"), \
             mock.patch.object(config, "QUARANTINE_DIR", "/data/quarantine"):
            self.assertTrue(is_protected_path("/data/backup_storage/x"))
            self.assertTrue(is_protected_path("/data/quarantine"))
            self.assertFalse(is_protected_path("/data/other/x"))
            self.assertFalse(is_protected_path(""))
        # Explicit roots override config (benchmark use).
        self.assertTrue(
            is_protected_path("/tmp/victim/backup/s.bin",
                              protected_roots=("/tmp/victim/backup",))
        )
        self.assertFalse(
            is_protected_path("/tmp/victim/documents/n.txt",
                              protected_roots=("/tmp/victim/backup",))
        )

    def test_cmdline_scan_finds_tamper_signatures(self):
        class FakeProc:
            def __init__(self, pid, name, cmdline):
                self.info = {"pid": pid, "name": name, "cmdline": cmdline}

        with mock.patch.object(config, "BACKUP_DIR", "/b"), \
             mock.patch.object(config, "QUARANTINE_DIR", "/q"), \
             mock.patch(
                 "monitoring.defense_guard.psutil.process_iter",
                 return_value=[
                     FakeProc(100, "python", ["python", "app.py"]),
                     FakeProc(200, "vssadmin.exe",
                              ["vssadmin", "delete", "shadows",
                               "/all", "/quiet"]),
                 ],
             ) as iter_mock:
            # Reset the TTL cache between tests.
            with mock.patch("monitoring.defense_guard.time.time",
                            return_value=1e12):
                hits = scan_process_cmdlines()
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["pid"], 200)
            self.assertIn("Shadow Copy", hits[0]["signature"])
            # Second call within the TTL uses the cache.
            with mock.patch("monitoring.defense_guard.time.time",
                            return_value=1e12 + 0.5):
                again = scan_process_cmdlines()
            self.assertEqual(again, hits)
            self.assertEqual(iter_mock.call_count, 1)

    def test_collect_flags_on_protected_deletion(self):
        event = {
            "event_type": "DELETED",
            "file_path": "/data/backup_storage/snap.bin",
            "threat_score": 0.0,
        }
        with mock.patch.object(config, "BACKUP_DIR", "/data/backup_storage"), \
             mock.patch.object(config, "QUARANTINE_DIR", "/q"):
            flags = collect_threat_flags(event)
        self.assertTrue(flags["defense_tamper"])
        self.assertTrue(flags["defense_tamper_evidence"])

    def test_collect_flags_on_ransom_note_create(self):
        path = self._note_path()
        event = {
            "event_type": "CREATED",
            "file_path": path,
            "threat_score": 0.0,
        }
        # The note is threaty, which triggers a real cmdline scan; pin
        # it so this test stays deterministic on any machine.
        import monitoring.defense_guard as guard
        with mock.patch.object(guard, "scan_process_cmdlines",
                               return_value=[]):
            flags = collect_threat_flags(event)
        self.assertTrue(flags["ransom_note"])
        self.assertFalse(flags["defense_tamper"])

    def test_clean_event_gets_no_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "planning.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(CLEAN_DOC)
            event = {
                "event_type": "CREATED",
                "file_path": path,
                "threat_score": 0.0,
            }
            flags = collect_threat_flags(event)
        self.assertFalse(flags["ransom_note"])
        self.assertFalse(flags["defense_tamper"])

    def _note_path(self) -> str:
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "Restore-My-Files.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(NOTE_TEXT)
        return path


class DecisionEscalationTests(unittest.TestCase):
    def test_ransom_note_forces_quarantine(self):
        event = {
            "entropy_overall": 0.0,
            "entropy_delta": 0.0,
            "events_per_sec": 0.0,
            "threat_score": 0.0,
            "file_extension": ".txt",
            "ransom_note": True,
            "ransom_note_evidence": ["filename matches known note"],
        }
        self.assertEqual(make_decision(event),
                         config.ACTION_TERMINATE_QUARANTINE)

    def test_defense_tamper_forces_quarantine(self):
        event = {
            "entropy_overall": 0.0,
            "entropy_delta": 0.0,
            "events_per_sec": 0.0,
            "threat_score": 0.0,
            "file_extension": ".bin",
            "defense_tamper": True,
            "defense_tamper_evidence": ["deletion of protected path"],
        }
        self.assertEqual(make_decision(event),
                         config.ACTION_TERMINATE_QUARANTINE)

    def test_existing_entropy_behavior_unchanged(self):
        """No flags: the classic unknown-extension high-entropy alert."""
        event = {
            "entropy_overall": 8.0,
            "entropy_delta": 0.0,
            "events_per_sec": 0.0,
            "threat_score": 40.0,
            "file_extension": ".locked",
        }
        self.assertEqual(make_decision(event), config.ACTION_ALERT)


class ProtectedStoreMonitorTests(unittest.TestCase):
    """The defender's own stores must be watched for DELETIONS only."""

    @classmethod
    def setUpClass(cls):
        # Constructed but never started — no scheduler, no file handles.
        cls.monitor = FileMonitor()
        cls.backup_blob = os.path.join(
            config.BACKUP_DIR, "versions", "a" * 64
        )
        cls.victim_file = os.path.join(
            config.WATCH_FOLDERS[0], "Documents", "notes.txt"
        )

    def test_default_stores_are_the_defense_stores(self):
        self.assertIn(config.BACKUP_DIR, self.monitor.protected_stores)
        self.assertIn(config.QUARANTINE_DIR, self.monitor.protected_stores)

    def test_backup_deletion_is_not_ignored(self):
        self.assertFalse(
            self.monitor.handler._should_ignore("DELETED", self.backup_blob)
        )

    def test_backup_write_is_ignored(self):
        # The defender's own capture writes must stay silent (feedback loop).
        self.assertTrue(
            self.monitor.handler._should_ignore("CREATED", self.backup_blob)
        )

    def test_backup_manifest_rewrite_is_exempt(self):
        # os.replace() rewrites the manifest on every capture; the old
        # copy is DELETED. Must not be flagged as tampering.
        manifest = os.path.join(config.BACKUP_DIR, "manifest.json")
        self.assertTrue(
            self.monitor.handler._should_ignore("DELETED", manifest)
        )

    def test_victim_deletion_behaves_as_before(self):
        # Victim-tree events are governed by the normal rules (not ignored
        # as defense-store writes).
        self.assertFalse(
            self.monitor.handler._should_ignore("CREATED", self.victim_file)
        )


if __name__ == "__main__":
    unittest.main()
