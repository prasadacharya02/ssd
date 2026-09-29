"""Attacker operator console: bundle serving, telemetry, and exposure limits.

Covers the redesigned console (attacker-ui -> attacker_server/static/console)
without launching a real attack process: the HTTP surface is exercised against
a throwaway server on an ephemeral port.
"""

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from attacker_server import app as attacker_app


class _ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), attacker_app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get(self, path):
        with urlopen(self.base + path, timeout=10) as response:
            return response.status, response.read().decode("utf-8")

    def head(self, path):
        request = Request(self.base + path, method="HEAD")
        with urlopen(request, timeout=10) as response:
            return response.status, response.headers

    def post(self, path, payload=None, token=None):
        body = json.dumps(payload or {}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(self.base + path, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))


class ConsoleDeliveryTests(_ServerCase):
    def test_root_serves_a_console_with_runtime_values_injected(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("window.__ENTROPY_CONSOLE__", body)
        # Placeholders must never reach the browser unresolved.
        self.assertNotIn("__CONTROL_TOKEN__", body)
        self.assertNotIn("__VICTIM_URL__", body)

    def test_root_prefers_the_built_bundle(self):
        if not attacker_app.console_index_available():
            self.skipTest("console bundle not built")

        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(attacker_app.CONSOLE_URL_PREFIX, body)

        # The legacy URL still resolves to a working console.
        legacy_status, legacy_body = self.get("/attacker.html")
        self.assertEqual(legacy_status, 200)
        self.assertIn("__ENTROPY_CONSOLE__", legacy_body)

    def test_root_falls_back_to_the_legacy_single_file_console(self):
        with mock.patch.object(attacker_app, "console_index_available", lambda: False):
            status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("fs0c13ty", body)

    def test_console_assets_are_served_with_script_content_type(self):
        if not attacker_app.console_index_available():
            self.skipTest("console bundle not built")

        _, index = self.get("/")
        marker = 'src="' + attacker_app.CONSOLE_URL_PREFIX
        self.assertIn(marker, index)
        asset_path = index.split(marker, 1)[1].split('"', 1)[0]
        asset_url = attacker_app.CONSOLE_URL_PREFIX + asset_path

        with urlopen(self.base + asset_url, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("javascript", response.headers["Content-Type"])
            self.assertGreater(len(response.read()), 1000)

    def test_console_assets_reject_traversal(self):
        for path in (
            "/static/console/../../config.py",
            "/static/console/%2e%2e%2f%2e%2e%2fconfig.py",
            "/static/console/..%2Frequirements.txt",
        ):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as context:
                    self.get(path)
                self.assertEqual(context.exception.code, 404)

    def test_head_requests_stay_inside_the_services_own_routes(self):
        with self.assertRaises(HTTPError) as context:
            self.head("/config.py")
        self.assertEqual(context.exception.code, 404)

        status, headers = self.head("/")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Length"], "0")


class ConsoleTelemetryTests(_ServerCase):
    def test_stats_exposes_the_fields_the_console_renders(self):
        status, body = self.get("/api/stats")
        self.assertEqual(status, 200)
        payload = json.loads(body)

        for key in (
            "active",
            "phase",
            "paused",
            "progress",
            "files_hit",
            "files_per_second",
            "elapsed_seconds",
            "exit_code",
            "defender_killed",
            "log",
            "victim",
        ):
            self.assertIn(key, payload)

        self.assertIsInstance(payload["log"], list)
        self.assertIn("total", payload["victim"])

    def test_targets_describes_the_victim_estate_read_only(self):
        status, body = self.get("/api/targets")
        self.assertEqual(status, 200)
        payload = json.loads(body)

        for key in ("exists", "total", "bytes", "attackable", "locked", "notes", "folders", "extensions"):
            self.assertIn(key, payload)

        self.assertIsInstance(payload["folders"], list)
        self.assertIsInstance(payload["extensions"], list)

        # Aggregates only: the console never receives file paths or contents.
        serialized = json.dumps(payload)
        self.assertNotIn("user_files/", serialized)

    def test_estate_snapshot_folders_and_extensions_reconcile(self):
        snapshot = attacker_app.estate_snapshot()
        self.assertEqual(
            snapshot["total"], sum(item["files"] for item in snapshot["folders"])
        )
        self.assertEqual(
            snapshot["total"], sum(item["files"] for item in snapshot["extensions"])
        )
        self.assertEqual(
            snapshot["bytes"], sum(item["bytes"] for item in snapshot["folders"])
        )

    def test_log_export_carries_a_header_and_timestamps(self):
        status, body = self.get("/api/log")
        self.assertEqual(status, 200)
        self.assertIn("# ENTROPY attacker console export", body)


class ControlAuthorizationTests(_ServerCase):
    def test_configured_token_blocks_loopback_requests_without_a_bearer_header(self):
        with mock.patch.object(attacker_app.config, "CONTROL_TOKEN", "entropy-lab"):
            status, payload = self.post("/api/stop")
            self.assertEqual(status, 403)
            self.assertFalse(payload["ok"])

    def test_configured_token_accepts_the_matching_bearer_header(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            control = os.path.join(directory, "attacker_control.json")
            with mock.patch.object(attacker_app.config, "CONTROL_TOKEN", "entropy-lab"), \
                 mock.patch.object(attacker_app, "_control_path", control):
                status, payload = self.post(
                    "/api/speed", {"factor": 2.0}, token="entropy-lab"
                )
                self.assertEqual(status, 200)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["speed_factor"], 2.0)

    def test_read_only_routes_need_no_token(self):
        with mock.patch.object(attacker_app.config, "CONTROL_TOKEN", "entropy-lab"):
            status, _ = self.get("/api/families")
            self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
