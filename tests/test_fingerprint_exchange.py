"""Federated threat-fingerprint exchange (step 1: the registry)."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

import config
import monitoring.pipeline_runner as runner
from blockchain.fingerprint_exchange import (FingerprintExchange,
                                             default_node_id)


class FingerprintExchangeTests(unittest.TestCase):
    """Store-level behaviour: one shared registry, many node views."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="exchange_test_")
        self.db = os.path.join(self.tmp, "exchange.db")
        self.node_a = FingerprintExchange(self.db, node_id="node-a")
        self.node_b = FingerprintExchange(self.db, node_id="node-b")

    def tearDown(self):
        self.node_a.close()
        self.node_b.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_register_and_lookup_roundtrip(self):
        fp = "ab" * 32
        rec = self.node_a.register(fp, file_extension=".txt",
                                   file_size=1234, evidence="burst")
        self.assertEqual(rec["fingerprint"], fp)
        self.assertEqual(rec["sightings"], 1)
        self.assertEqual(rec["sources"], ["node-a"])
        self.assertEqual(rec["file_extension"], ".txt")

        # node-b sees the same record — this is the shared memory.
        seen = self.node_b.lookup(fp)
        self.assertIsNotNone(seen)
        self.assertEqual(seen["sources"], ["node-a"])
        self.assertEqual(seen["first_evidence"], "burst")

    def test_lookup_miss_returns_none(self):
        self.assertIsNone(self.node_b.lookup("ff" * 32))
        self.assertIsNone(self.node_b.lookup(""))
        self.assertIsNone(self.node_b.lookup(None))

    def test_upsert_increments_sightings_and_merges_sources(self):
        fp = "cd" * 32
        self.node_a.register(fp)
        rec = self.node_b.register(fp, reference="tx-2")
        self.assertEqual(rec["sightings"], 2)
        self.assertEqual(sorted(rec["sources"]), ["node-a", "node-b"])
        # First-sight metadata is preserved, not overwritten.
        self.assertEqual(rec["first_seen"], rec["first_seen"])
        self.assertEqual(rec["latest_reference"], "tx-2")

    def test_same_node_twice_is_two_sightings_one_source(self):
        fp = "11" * 32
        self.node_a.register(fp)
        rec = self.node_a.register(fp)
        self.assertEqual(rec["sightings"], 2)
        self.assertEqual(rec["sources"], ["node-a"])

    def test_fingerprint_is_case_and_whitespace_insensitive(self):
        fp = "ab" * 32
        self.node_a.register(fp.upper())
        self.assertEqual(self.node_a.lookup(f" {fp} ")["sightings"], 1)

    def test_empty_fingerprint_rejected(self):
        with self.assertRaises(ValueError):
            self.node_a.register("")
        with self.assertRaises(ValueError):
            self.node_a.register("   ")

    def test_default_node_id_is_stable_and_named(self):
        with mock.patch.object(config, "EXCHANGE_NODE_ID", ""):
            first, second = default_node_id(), default_node_id()
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("node-"))
        with mock.patch.object(config, "EXCHANGE_NODE_ID", "tenant-42"):
            self.assertEqual(default_node_id(), "tenant-42")


class ExchangeResponseIntegrationTests(unittest.TestCase):
    """execute_response shares confirmed-threat fingerprints — and only
    those, and only when it holds the real content hash."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="exchange_int_")
        self.db = os.path.join(self.tmp, "exchange.db")
        self.exchange = FingerprintExchange(self.db, node_id="node-test")
        self.file = os.path.join(self.tmp, "report.pdf")
        with open(self.file, "w") as fh:
            fh.write("encrypted payload")
        self.file_hash = "ef" * 32

    def tearDown(self):
        self.exchange.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _event(self, **overrides):
        event = {
            "event_id": "e1",
            "timestamp": "2026-09-18T00:00:00",
            "event_type": "MODIFIED",
            "file_path": self.file,
            "file_extension": ".pdf",
            "file_size": 17,
            "entropy_overall": 7.9,
            "entropy_delta": 0.0,
            "events_per_sec": 0.0,
            "file_hash": self.file_hash,
            "threat_score": 90.0,
            "is_suspicious_speed": True,
        }
        event.update(overrides)
        return event

    def _run(self, action, event):
        class _Bc:
            def log_event(self, _e):
                pass
        with mock.patch.object(config, "DRY_RUN", True), \
             mock.patch.object(runner, "get_exchange",
                               lambda: self.exchange):
            return runner.execute_response(
                action, event, _Bc(), None,
                {"engine": "rules", "confidence": 1.0,
                 "explanation": "test incident"},
            )

    def test_confirmed_threat_shares_content_hash(self):
        self._run(config.ACTION_TERMINATE_QUARANTINE, self._event())
        rec = self.exchange.lookup(self.file_hash)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["sources"], ["node-test"])
        self.assertEqual(rec["file_extension"], ".pdf")
        self.assertIn("test incident", rec["first_evidence"])

    def test_alert_is_not_shared(self):
        self._run(config.ACTION_ALERT, self._event())
        self.assertIsNone(self.exchange.lookup(self.file_hash))
        self.assertEqual(self.exchange.count(), 0)

    def test_missing_content_hash_is_not_shared(self):
        # Defense-tamper on an already-deleted file: no content, no
        # fingerprint — a path hash must never be published.
        event = self._event(file_hash="")
        self._run(config.ACTION_TERMINATE_QUARANTINE, event)
        self.assertEqual(self.exchange.count(), 0)


if __name__ == "__main__":
    unittest.main()
