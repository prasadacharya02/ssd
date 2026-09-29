from pathlib import Path
import sqlite3
import tempfile
from unittest import mock
import unittest

import reset_test


class ResetUtilityTests(unittest.TestCase):
    def test_reset_clears_only_configured_runtime_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "events.db"
            quarantine = root / "quarantine"
            testing = root / "testing"
            blockchain = root / "blockchain"

            quarantine.mkdir()
            testing.mkdir()
            blockchain.mkdir()
            (quarantine / "sample.locked").write_text("x")
            (testing / "event.dat").write_text("x")
            (blockchain / "ledger.db").write_text("x")

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT)"
                )
                connection.execute("INSERT INTO events DEFAULT VALUES")

            fixture_result = {"files_created": 18}
            patches = (
                mock.patch.object(reset_test.config, "DB_PATH", str(database)),
                mock.patch.object(reset_test.config, "QUARANTINE_DIR", str(quarantine)),
                mock.patch.object(reset_test.config, "TESTING_DATA_DIR", str(testing)),
                mock.patch.object(reset_test.config, "BLOCKCHAIN_DIR", str(blockchain)),
                mock.patch.object(
                    reset_test,
                    "restore_all_files",
                    return_value=fixture_result,
                ),
            )

            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                result = reset_test.reset_runtime_state(quiet=True)

            with sqlite3.connect(database) as connection:
                event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]

            self.assertEqual(event_count, 0)
            self.assertEqual(list(quarantine.iterdir()), [])
            self.assertEqual(list(testing.iterdir()), [])
            self.assertFalse((blockchain / "ledger.db").exists())
            self.assertEqual(result["fixtures"], fixture_result)


if __name__ == "__main__":
    unittest.main()
