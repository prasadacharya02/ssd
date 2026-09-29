import json
import tempfile
import unittest
from pathlib import Path

from data.training_schema import (
    REQUIRED_FIELDS,
    generate_dataset,
    load_samples,
    validate_sample,
    write_dataset,
)


class TrainingSchemaTests(unittest.TestCase):
    def test_same_seed_is_deterministic_and_split(self):
        train_a, eval_a = generate_dataset(seed=42, normal_count=20, ransomware_count=20)
        train_b, eval_b = generate_dataset(seed=42, normal_count=20, ransomware_count=20)
        self.assertEqual(train_a, train_b)
        self.assertEqual(eval_a, eval_b)
        self.assertEqual(train_a["schema_version"], 1)
        self.assertTrue(eval_a["samples"])
        self.assertTrue(all(validate_sample(s) for s in train_a["samples"]))

    def test_write_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            train_path, eval_path = write_dataset(
                directory, seed=7, normal_count=8, ransomware_count=8
            )
            samples = load_samples(train_path)
            self.assertTrue(samples)
            self.assertTrue(all(field in samples[0] for field in REQUIRED_FIELDS))
            payload = json.loads(Path(eval_path).read_text(encoding="utf-8"))
            self.assertEqual(payload["split"], "eval")


if __name__ == "__main__":
    unittest.main()
