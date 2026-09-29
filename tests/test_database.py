import sqlite3
import tempfile
from pathlib import Path
import unittest

from storage.database import SCHEMA_VERSION, init_db


class DatabaseSchemaTests(unittest.TestCase):
    def test_shared_initializer_creates_versioned_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = init_db(str(Path(directory) / "events.db"))
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                version = connection.execute(
                    "SELECT value FROM schema_meta WHERE key='schema_version'"
                ).fetchone()[0]
            finally:
                connection.close()

            self.assertIn("events", tables)
            self.assertIn("schema_meta", tables)
            self.assertEqual(version, str(SCHEMA_VERSION))

    def test_existing_events_table_is_migrated_without_data_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy.db"
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT)"
                )
                connection.execute("INSERT INTO events DEFAULT VALUES")
                connection.commit()

            connection = init_db(str(database))
            try:
                count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(events)")
                }
            finally:
                connection.close()

            self.assertEqual(count, 1)
            self.assertTrue(
                {"timestamp", "file_path", "action", "status", "requested_action", "outcome"}
                <= columns
            )


if __name__ == "__main__":
    unittest.main()
