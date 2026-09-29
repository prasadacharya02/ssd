"""Random Forest second classifier: model, engine wiring, safety.

The classifier itself needs scikit-learn (an optional dependency,
like torch/web3): without it these tests skip. Engine-selection tests
that only need the decision layer run regardless.
"""

import json
import os
import shutil
import tempfile
import unittest

import config
from monitoring.pipeline_runner import (DecisionEngine, _RF_AVAILABLE)

MODEL_PATH = os.path.join(config.AI_DIR, "rf_weights.json")

HAS_SKLEARN = _RF_AVAILABLE
MODEL_SHIPPED = os.path.exists(MODEL_PATH)


def _attack_event(**over):
    event = {
        "event_id": "t",
        "timestamp": "2026-09-18T03:00:00",
        "file_path": "/v/docs/a.txt.locked",
        "file_extension": ".locked",
        "entropy_overall": 8.0,
        "entropy_delta": 4.6,
        "events_per_sec": 12.0,
        "events_in_window": 30,
        "ext_changed": True,
        "process": {"name": "exploit.sh", "pid": 999, "age_seconds": 5},
    }
    event.update(over)
    return event


def _legit_event(**over):
    event = {
        "event_id": "t",
        "timestamp": "2026-09-18T09:00:00",
        "file_path": "/v/pics/p.jpg",
        "file_extension": ".jpg",
        "entropy_overall": 7.2,
        "entropy_delta": 0.1,
        "events_per_sec": 2.0,
        "events_in_window": 4,
        "ext_changed": False,
        "process": {"name": "explorer.exe", "pid": 100, "age_seconds": 900},
    }
    event.update(over)
    return event


@unittest.skipUnless(HAS_SKLEARN, "scikit-learn not installed")
class RFModelTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rf_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _train_small(self, path):
        from ai import rf_model
        train, evaluate = rf_model.generate_dataset(
            seed=7, normal_count=200, ransomware_count=200,
        )
        model, metrics = rf_model.train_rf(
            train["samples"], evaluate["samples"], n_estimators=64,
        )
        rf_model.save_model(model, metrics, path)
        return rf_model

    def test_train_save_load_roundtrip(self):
        rf = self._train_small(os.path.join(self.tmp, "m.json"))
        model, meta = rf.load_model(os.path.join(self.tmp, "m.json"))
        self.assertEqual(meta["schema_version"], rf.SCHEMA_VERSION)
        self.assertEqual(tuple(meta["features"]), rf.FEATURES)
        self.assertEqual(len(meta["features"]), 11)
        # Same features → same prediction after a roundtrip.
        x = rf.extract_features(_attack_event())
        proba = float(model.predict_proba([x])[0, 1])
        self.assertGreater(proba, 0.9)

    def test_schema_mismatch_rejected(self):
        path = os.path.join(self.tmp, "m.json")
        rf = self._train_small(path)
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        payload["schema_version"] = 99
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        with self.assertRaises(ValueError):
            rf.load_model(path)

    def test_in_normal_range_values(self):
        rf = self._train_small(os.path.join(self.tmp, "m.json"))
        # .jpg normal range (7.0, 7.8)
        self.assertEqual(rf.in_normal_range(".jpg", 7.2), 1.0)
        # .txt normal range (3.0, 5.5) — 8.0 is out of range
        self.assertEqual(rf.in_normal_range(".txt", 8.0), -1.0)
        # unknown extension → no range info
        self.assertEqual(rf.in_normal_range(".locked", 8.0), 0.0)

    def test_attack_scores_higher_than_legit(self):
        rf = self._train_small(os.path.join(self.tmp, "m.json"))
        engine = rf.RFEngine(os.path.join(self.tmp, "m.json"))
        atk = engine.score(_attack_event())
        legit = engine.score(_legit_event(pid=200))
        self.assertGreaterEqual(atk["action"], config.ACTION_ALERT)
        self.assertGreaterEqual(atk["risk"], 70)
        # An in-range photo must not be quarantined.
        self.assertLess(legit["action"], config.ACTION_TERMINATE_QUARANTINE)
        self.assertGreater(atk["risk"], legit["risk"])

    def test_explanation_shape(self):
        rf = self._train_small(os.path.join(self.tmp, "m.json"))
        engine = rf.RFEngine(os.path.join(self.tmp, "m.json"))
        result = engine.score(_attack_event())
        self.assertIn("risk", result["explanation"])
        self.assertEqual(len(result["top_features"]), 3)
        for feature in result["top_features"]:
            self.assertIn(feature["feature"], rf.FEATURES)
            self.assertIn(feature["direction"], ("up", "down"))

    def test_deterministic_across_engines(self):
        path = os.path.join(self.tmp, "m.json")
        self._train_small(path)
        rf = self._train_small(path)
        a = rf.RFEngine(path).score(_attack_event())
        b = rf.RFEngine(path).score(_attack_event())
        self.assertEqual(a["risk"], b["risk"])
        self.assertEqual(a["explanation"], b["explanation"])


class DecisionEngineSelectionTests(unittest.TestCase):
    """Engine selection + safety invariants (no sklearn needed)."""

    def test_auto_stays_rules_even_with_trained_model(self):
        # The 0-false-quarantine safety bar is the default, even when
        # a trained RF model exists.
        self.assertEqual(DecisionEngine().engine_name(), "rules")
        self.assertEqual(
            DecisionEngine(engine="auto").engine_name(), "rules"
        )

    def test_forced_rules(self):
        self.assertEqual(DecisionEngine(engine="rules").engine_name(),
                         "rules")

    def test_unavailable_engine_falls_back_to_rules(self):
        # No dqn weights ship in the repo → forced dqn falls back.
        self.assertEqual(DecisionEngine(engine="dqn").engine_name(),
                         "rules")

    def test_rf_engine_selection(self):
        if not (HAS_SKLEARN and MODEL_SHIPPED):
            self.skipTest("RF model not present in this checkout")
        self.assertEqual(DecisionEngine(engine="rf").engine_name(), "rf")

    def test_hard_confirmation_overrides_rf(self):
        """A ransom note is a confirmed incident on its own — no
        model (even the high-recall RF) may down-grade it."""
        if not (HAS_SKLEARN and MODEL_SHIPPED):
            self.skipTest("RF model not present in this checkout")
        engine = DecisionEngine(engine="rf")
        decision = engine.decide(_legit_event(ransom_note=True,
                                              ransom_note_evidence=["README.RECOVERY"]))
        self.assertEqual(decision["action"],
                         config.ACTION_TERMINATE_QUARANTINE)
        self.assertEqual(decision["engine"], "rf")
        self.assertIn("RANSOM NOTE", decision["explanation"])

    def test_single_sighting_cannot_quarantine_via_rf(self):
        """A single node's exchange sighting may raise an ignore to an
        alert but never quarantine (poison-node defence) — holds for
        the RF engine too."""
        if not (HAS_SKLEARN and MODEL_SHIPPED):
            self.skipTest("RF model not present in this checkout")
        engine = DecisionEngine(engine="rf")
        calm = _legit_event(
            known_threat=True, known_threat_confirmed=False,
            known_threat_evidence="1 node",
        )
        decision = engine.decide(calm)
        self.assertLessEqual(decision["action"], config.ACTION_ALERT)

    def test_rules_engine_still_used_by_default_decide(self):
        # The default engine must behave exactly like make_decision.
        from monitoring.pipeline_runner import make_decision
        engine = DecisionEngine()
        for event in (_attack_event(), _legit_event(),
                      _legit_event(entropy_overall=7.9,
                                   file_extension=".zip",
                                   file_path="/v/z.zip")):
            with self.subTest(event=event["file_path"]):
                decision = engine.decide(event)
                self.assertEqual(decision["engine"], "rules")
                self.assertEqual(decision["action"], make_decision(event))


if __name__ == "__main__":
    unittest.main()
