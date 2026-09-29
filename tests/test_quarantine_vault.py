"""Quarantine vault regressions: evidence handling, self-echo
suppression, fake-rename rejection and the PIN-gated vault API."""

import json
import os
import tempfile
import time
import unittest
from unittest import mock

import config
from monitoring.event_pipeline import _is_genuine_rename
from response.defender_actions import DefenderActions


class DefenderActionRegistryTests(unittest.TestCase):
    def test_restore_echo_matches_only_same_content(self):
        reg = DefenderActions()
        reg.record_restore("/v/a.txt", "abc")
        self.assertTrue(reg.is_restore_echo("/v/a.txt", "abc"))
        # Different content at the same path is a NEW change → analysed.
        self.assertFalse(reg.is_restore_echo("/v/a.txt", "evil"))

    def test_entries_expire(self):
        reg = DefenderActions(window=0.05)
        reg.record_moved_away("/v/a.txt")
        self.assertTrue(reg.is_own_removal("/v/a.txt"))
        time.sleep(0.1)
        self.assertFalse(reg.is_own_removal("/v/a.txt"))


class FakeRenameTests(unittest.TestCase):
    def test_inode_reuse_is_not_a_rename(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "Tax_Returns.pdf")
            dst = os.path.join(d, "Notes.txt")
            open(src, "w").close(); open(dst, "w").close()
            # Source still exists → not a genuine rename
            self.assertFalse(_is_genuine_rename(
                {"original_path": src, "dest_path": dst}))
            os.remove(src)
            self.assertTrue(_is_genuine_rename(
                {"original_path": src, "dest_path": dst}))


class QuarantineMoveTests(unittest.TestCase):
    def test_evidence_is_never_overwritten_and_read_only(self):
        from response.response_module import FileQuarantine
        with tempfile.TemporaryDirectory() as d:
            vault = os.path.join(d, "vault")
            with mock.patch.object(config, "QUARANTINE_DIR", vault), \
                 mock.patch.object(config, "DRY_RUN", False):
                q = FileQuarantine()
                paths = []
                for _ in range(3):
                    f = os.path.join(d, "doc.txt.locked")
                    with open(f, "wb") as h:
                        h.write(b"same ciphertext")
                    r = q.quarantine(f, event={
                        "response_kill": {"pid": 42, "name": "evil",
                                          "terminated": True}})
                    self.assertTrue(r["success"], r["message"])
                    paths.append(r["quarantine_path"])
                self.assertEqual(len(set(paths)), 3)
                for p in paths:
                    self.assertTrue(os.path.exists(p))
                    self.assertFalse(os.access(p, os.W_OK))
                    with open(p + ".meta.json") as h:
                        meta = json.load(h)
                    self.assertEqual(meta["terminated_process"]["pid"], 42)
                    self.assertEqual(meta["original_name"], "doc.txt.locked")
                for p in paths:
                    os.chmod(p, 0o600)


class StoreEvidenceResponseTests(unittest.TestCase):
    def test_files_in_vault_are_not_requarantined(self):
        from monitoring import pipeline_runner as pr
        with tempfile.TemporaryDirectory() as d:
            vault = os.path.join(d, "vault")
            os.makedirs(vault)
            ev = os.path.join(vault, "abc_doc.txt")
            with open(ev, "wb") as h:
                h.write(b"x" * 100)
            with mock.patch.object(config, "QUARANTINE_DIR", vault), \
                 mock.patch.object(config, "DRY_RUN", False), \
                 mock.patch.object(pr, "save_to_db"), \
                 mock.patch.object(pr, "generate_report", return_value=None):
                bc = mock.Mock()
                out = pr.execute_response(
                    config.ACTION_TERMINATE_QUARANTINE,
                    {"file_path": ev, "file_hash": "h" * 64,
                     "event_type": "DELETED"},
                    bc, None, {}, backup=mock.Mock(), exchange=mock.Mock())
            self.assertTrue(os.path.exists(ev))
            self.assertEqual(os.listdir(vault), ["abc_doc.txt"])
            self.assertNotIn("QUARANTINED", out)


class VaultApiTests(unittest.TestCase):
    def setUp(self):
        import importlib
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = os.path.join(self.tmp.name, "vault")
        os.makedirs(self.vault)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "victim_app", os.path.join(config.BASE_DIR, "victim_server",
                                       "app.py"))
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.QUARANTINE_FILES = self.vault
        f = os.path.join(self.vault, "abcdef_Budget.xlsx.WNCRY")
        with open(f, "wb") as h:
            h.write(os.urandom(64))
        with open(f + ".meta.json", "w") as h:
            json.dump({
                "original_path": os.path.join(self.mod.USER_FILES,
                                              "Documents", "Budget.xlsx"),
                "original_name": "Budget.xlsx.WNCRY",
                "quarantine_time": "2026-09-23T10:00:00",
                "fingerprint": "f" * 64, "entropy": 7.99,
                "terminated_process": {"pid": 4242, "name": "python3",
                                       "terminated": True},
            }, h)
        self.client = self.mod.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_locked_without_pin(self):
        self.assertEqual(self.client.get("/api/quarantine").status_code, 401)
        self.assertEqual(
            self.client.get("/api/files/Quarantine").status_code, 401)

    def test_wrong_pin_rejected(self):
        r = self.client.post("/api/vault/login", json={"pin": "0000"})
        self.assertEqual(r.status_code, 403)

    def test_pin_unlocks_and_shows_containment_record(self):
        r = self.client.post("/api/vault/login",
                             json={"pin": self.mod.VAULT_PIN})
        self.assertTrue(r.get_json()["ok"])
        data = self.client.get("/api/quarantine").get_json()
        self.assertEqual(data["count"], 1)
        f = data["files"][0]
        self.assertEqual(f["from_folder"], "Documents")
        self.assertTrue(f["process_killed"])
        self.assertEqual(f["killed_pid"], 4242)
        self.assertEqual(data["processes_killed"][0]["pid"], 4242)
        prev = self.client.get(
            "/api/file/Quarantine/abcdef_Budget.xlsx.WNCRY").get_json()
        self.assertIn("PID 4242", prev["content"])


if __name__ == "__main__":
    unittest.main()
