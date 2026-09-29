"""Multi-node federated exchange simulation invariants."""

import hashlib
import os
import shutil
import tempfile
import unittest
from unittest import mock

import config
import monitoring.pipeline_runner as runner
from benchmark.exchange_simulation import (run_simulation, NOTE_BYTES,
                                           payload_bytes)
from blockchain.fingerprint_exchange import FingerprintExchange


class ExchangeSimulationTests(unittest.TestCase):
    """The 'have we seen this before?' claim, end to end."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="exchange_sim_test_")
        # The simulation drives the real response path; keep the
        # canonical store out of it and keep forensic reports local.
        cls._patchers = [
            mock.patch.object(runner, "get_exchange",
                                       side_effect=AssertionError(
                                           "canonical store must not be "
                                           "used by the simulation")),
            mock.patch.object(config, "REPORTS_DIR",
                                       os.path.join(cls.tmp, "reports")),
        ]
        for p in cls._patchers:
            p.start()
        cls.report = run_simulation(base_dir=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        for p in cls._patchers:
            p.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _phase(self, name) -> dict:
        for phase in self.report["phases"]:
            if phase["phase"] == name:
                return phase
        raise AssertionError(f"phase {name} missing")

    def test_cold_start_is_alert_only(self):
        # Empty exchange: the locally ambiguous file is only an alert.
        result = self._phase("1_cold_start")["result"]
        self.assertEqual(result["action"], config.ACTION_ALERT)
        self.assertFalse(result["known_threat"])

    def test_single_sighting_corroborates_but_does_not_quarantine(self):
        # One node's sighting weighs the score (+25) but can never
        # quarantine alone: a poisoned node must not destroy files.
        result = self._phase("3_single_sighting")["result"]
        self.assertEqual(result["action"], config.ACTION_ALERT)
        self.assertTrue(result["known_threat"])
        self.assertFalse(result["known_threat_confirmed"])
        self.assertIn("CORROBORATED BY EXCHANGE", result["explanation"])

    def test_warm_start_confirms_and_quarantines(self):
        # >= threshold independent nodes: the same locally-ambiguous
        # file is a confirmed threat on a fresh node with zero history.
        result = self._phase("5_warm_start")["result"]
        self.assertEqual(result["action"],
                         config.ACTION_TERMINATE_QUARANTINE)
        self.assertTrue(result["known_threat_confirmed"])
        self.assertIn("CONFIRMED BY EXCHANGE", result["explanation"])

    def test_seeding_tenants_quarantined_both_strain_files(self):
        for name in ("2_seeding_alpha", "4_seeding_bravo"):
            phase = self._phase(name)
            for rec in phase["ops"]:
                self.assertEqual(
                    rec["action"], config.ACTION_TERMINATE_QUARANTINE,
                    f"{name}: {rec['file']} should quarantine",
                )

    def test_exchange_is_threat_only(self):
        # Legitimate work produces no quarantine and adds no records.
        phase = self._phase("6_workload_honesty")
        for rec in phase["ops"]:
            self.assertNotEqual(
                rec["action"], config.ACTION_TERMINATE_QUARANTINE,
                f"legitimate file quarantined: {rec['file']}",
            )
        self.assertEqual(phase["exchange_count_before"],
                         phase["exchange_count_after"])

    def test_payload_fingerprint_has_two_independent_sources(self):
        # The exchange's cross-node memory, verified against the
        # actual store on disk.
        store = FingerprintExchange(
            os.path.join(self.tmp, "exchange.db"), node_id="test"
        )
        try:
            payload_fp = hashlib.sha256(payload_bytes()).hexdigest()
            rec = store.lookup(payload_fp)
            self.assertIsNotNone(rec)
            self.assertGreaterEqual(len(rec["sources"]), 2)
            self.assertNotIn("test", rec["sources"])
            # The ransom note was shared by the two seeding tenants.
            note_fp = hashlib.sha256(NOTE_BYTES).hexdigest()
            note_rec = store.lookup(note_fp)
            self.assertIsNotNone(note_rec)
            self.assertEqual(len(note_rec["sources"]), 2)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
