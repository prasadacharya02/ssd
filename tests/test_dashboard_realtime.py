"""Regression tests for the SOC dashboard real-time path.

Covers the three bugs that made the dashboard show nothing:
  1. lab.py kept an EMPTY ENTROPY_WATCH_FOLDERS from a .env copied from
     .env.example, so the pipeline watched data/testing, not the victim.
  2. The dashboard loaded /socket.io/socket.io.js, which python-socketio
     5.x does not serve (HTTP 400) — the live channel never connected.
  3. There was no way to see whether the pipeline was running at all.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import lab
from storage.database import (connect, init_db, read_pipeline_heartbeat,
                              write_pipeline_heartbeat)

ROOT = Path(__file__).resolve().parents[1]
VICTIM = str((ROOT / "victim_server" / "user_files").resolve())


def _resolved(env):
    return [str((ROOT / f).resolve())
            for f in env["ENTROPY_WATCH_FOLDERS"].split(",")]


class LabWatchFolderTests(unittest.TestCase):
    def test_empty_watch_folders_from_dotenv_still_watch_victim(self):
        with mock.patch.dict(os.environ, {"ENTROPY_WATCH_FOLDERS": ""}):
            self.assertIn(VICTIM, _resolved(lab._env()))

    def test_unset_watch_folders_watch_victim(self):
        env = {k: v for k, v in os.environ.items()
               if k != "ENTROPY_WATCH_FOLDERS"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIn(VICTIM, _resolved(lab._env()))

    def test_extra_folders_are_kept_and_victim_added(self):
        with mock.patch.dict(os.environ,
                             {"ENTROPY_WATCH_FOLDERS": "data/testing"}):
            folders = _resolved(lab._env())
        self.assertIn(VICTIM, folders)
        self.assertIn(str((ROOT / "data" / "testing").resolve()), folders)

    def test_victim_not_duplicated(self):
        with mock.patch.dict(
                os.environ,
                {"ENTROPY_WATCH_FOLDERS": "victim_server/user_files"}):
            self.assertEqual(_resolved(lab._env()).count(VICTIM), 1)

    def test_empty_dry_run_defaults_to_live(self):
        with mock.patch.dict(os.environ, {"ENTROPY_DRY_RUN": ""}):
            self.assertEqual(lab._env()["ENTROPY_DRY_RUN"], "false")


class PipelineHeartbeatTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.db")
            init_db(path).close()
            conn = connect(path)
            self.assertIsNone(read_pipeline_heartbeat(conn))
            write_pipeline_heartbeat(
                conn, started_at=time.time(), pid=123,
                watch_folders=[VICTIM], dry_run=False, engine="rules",
                stats={"received": 5})
            hb = read_pipeline_heartbeat(conn)
            conn.close()
        self.assertEqual(hb["watch_folders"], [VICTIM])
        self.assertFalse(hb["dry_run"])
        self.assertEqual(hb["stats"]["received"], 5)


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        import app as dashboard
        self.dashboard = dashboard
        self.client = dashboard.app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "dash.db")
        init_db(self.db).close()
        self.patch = mock.patch("app.get_db",
                                side_effect=lambda: connect(self.db))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _beat(self, age=0.0, folders=(VICTIM,)):
        conn = connect(self.db)
        write_pipeline_heartbeat(conn, started_at=time.time(), pid=1,
                                 watch_folders=list(folders),
                                 dry_run=False, engine="rules", stats={})
        conn.execute("UPDATE pipeline_status SET heartbeat=?",
                     (time.time() - age,))
        conn.commit()
        conn.close()

    def test_offline_when_pipeline_never_ran(self):
        data = self.client.get("/api/pipeline").get_json()
        self.assertFalse(data["online"])

    def test_online_and_watching_victim(self):
        self._beat()
        data = self.client.get("/api/pipeline").get_json()
        self.assertTrue(data["online"])
        self.assertTrue(data["watching_victim"])

    def test_stale_heartbeat_is_offline(self):
        self._beat(age=60)
        self.assertFalse(self.client.get("/api/pipeline").get_json()["online"])

    def test_wrong_folder_is_flagged(self):
        self._beat(folders=[str(ROOT / "data" / "testing")])
        data = self.client.get("/api/pipeline").get_json()
        self.assertFalse(data["watching_victim"])

    def test_dashboard_uses_locally_served_client_libraries(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('src="/socket.io/socket.io.js"', html)
        for lib in ("vendor/socket.io.min.js", "vendor/chart.umd.min.js"):
            self.assertIn(lib, html)
            resp = self.client.get("/static/" + lib)
            self.assertEqual(resp.status_code, 200)
            resp.close()


if __name__ == "__main__":
    unittest.main()
