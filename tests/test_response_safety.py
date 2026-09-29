import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from monitoring.watchdog_monitor import ProcessFinder
from response.response_module import FileQuarantine, ProcessTerminator
from storage.database import SCHEMA_VERSION, init_db


class ResponseSafetyTests(unittest.TestCase):
    def test_incomplete_identity_is_refused_even_in_dry_run(self):
        with mock.patch.object(config, "DRY_RUN", True):
            result = ProcessTerminator().terminate(0, process_name=None)
        self.assertFalse(result["success"])
        self.assertIn("Refused", result["message"])

    def test_whitelist_is_never_terminated(self):
        with mock.patch.object(config, "DRY_RUN", False):
            result = ProcessTerminator().terminate(4004, process_name="svchost.exe")
        self.assertFalse(result["success"])
        self.assertIn("whitelist", result["message"].lower())

    def test_dry_run_does_not_move_quarantine_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "secret.txt"
            target.write_text("keep me", encoding="utf-8")
            quarantine_dir = Path(directory) / "q"
            with mock.patch.object(config, "DRY_RUN", True), \
                 mock.patch.object(config, "QUARANTINE_DIR", str(quarantine_dir)):
                result = FileQuarantine().quarantine(str(target))
            self.assertTrue(result["success"])
            self.assertTrue(target.exists())
            self.assertIn("Dry-run", result["message"])

    def test_recent_process_guess_is_not_verified(self):
        finder = ProcessFinder()
        with mock.patch.object(finder, "_find_by_open_file", return_value=None), \
             mock.patch.object(
                 finder,
                 "_find_recent_suspicious",
                 return_value={"pid": 1234, "name": "python", "identity_verified": False},
             ):
            info = finder.get_process_info("/tmp/example.txt")
        self.assertEqual(info["attribution_source"], "recent_process_guess")
        self.assertFalse(info["identity_verified"])

    def test_schema_records_requested_action_and_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = init_db(str(Path(directory) / "events.db"))
            try:
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(events)")
                }
                version = connection.execute(
                    "SELECT value FROM schema_meta WHERE key='schema_version'"
                ).fetchone()[0]
            finally:
                connection.close()
        self.assertEqual(version, str(SCHEMA_VERSION))
        self.assertTrue({"requested_action", "outcome", "dry_run"} <= columns)


if __name__ == "__main__":
    unittest.main()
