import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REQUIRED_SERVICE_MODULES = (
    "flask",
    "flask_socketio",
    "watchdog",
    "psutil",
)
SERVICES_AVAILABLE = all(
    importlib.util.find_spec(module) is not None
    for module in REQUIRED_SERVICE_MODULES
)


@unittest.skipUnless(
    SERVICES_AVAILABLE,
    "web service integration dependencies are optional",
)
class ServiceIntegrationTests(unittest.TestCase):
    def test_victim_and_dashboard_health_routes(self):
        from app import app as dashboard_app
        from victim_server.app import app as victim_app
        from storage.database import init_db

        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "events.db")
            with mock.patch("config.DB_PATH", database):
                init_db(database).close()
                dashboard_client = dashboard_app.test_client()
                victim_client = victim_app.test_client()
                dashboard_response = dashboard_client.get("/api/stats")
                victim_response = victim_client.get("/api/folders")
                demo = dashboard_client.post("/api/demo/trigger")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("total", dashboard_response.get_json())
        self.assertEqual(victim_response.status_code, 200)
        self.assertIsInstance(victim_response.get_json(), list)
        self.assertEqual(demo.status_code, 409)

    def test_attacker_service_exposes_read_only_status_and_family_catalog(self):
        from attacker_server.app import Handler
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import urlopen
        import json

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            with urlopen(base + "/api/families") as response:
                families = json.load(response)
            with urlopen(base + "/api/stats") as response:
                stats = json.load(response)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertTrue(families)
        self.assertIn("active", stats)
        self.assertIn("victim", stats)


if __name__ == "__main__":
    unittest.main()
