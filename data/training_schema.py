"""Versioned, deterministic DQN training-data schema."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_FIELDS = (
    "label",
    "entropy_score",
    "entropy_delta",
    "files_per_sec",
    "ext_changed",
    "process_age_sec",
    "is_signed",
    "files_affected",
    "avg_entropy_hist",
    "is_known_process",
    "time_hour",
)


def _sample(rng: random.Random, ransomware: bool) -> dict[str, Any]:
    if ransomware:
        return {
            "label": 1,
            "entropy_score": rng.uniform(7.5, 8.0),
            "entropy_delta": rng.uniform(2.0, 5.0),
            "files_per_sec": rng.uniform(5.0, 50.0),
            "ext_changed": rng.randint(0, 1),
            "process_age_sec": rng.uniform(1, 60),
            "is_signed": 0,
            "files_affected": rng.randint(10, 200),
            "avg_entropy_hist": rng.uniform(7.0, 8.0),
            "is_known_process": 0,
            "time_hour": rng.randint(0, 23),
        }
    return {
        "label": 0,
        "entropy_score": rng.uniform(3.0, 6.5),
        "entropy_delta": rng.uniform(-0.3, 0.3),
        "files_per_sec": rng.uniform(0.01, 0.5),
        "ext_changed": 0,
        "process_age_sec": rng.uniform(300, 7200),
        "is_signed": rng.choice([0, 1]),
        "files_affected": rng.randint(1, 3),
        "avg_entropy_hist": rng.uniform(3.5, 6.0),
        "is_known_process": rng.choice([0, 1]),
        "time_hour": rng.randint(8, 20),
    }


def validate_sample(sample: dict) -> bool:
    return all(field in sample for field in REQUIRED_FIELDS) and sample["label"] in {0, 1}


def generate_dataset(
    *,
    seed: int = 1337,
    normal_count: int = 80,
    ransomware_count: int = 80,
    holdout: float = 0.25,
) -> tuple[dict, dict]:
    rng = random.Random(seed)
    samples = [_sample(rng, False) for _ in range(normal_count)]
    samples.extend(_sample(rng, True) for _ in range(ransomware_count))
    rng.shuffle(samples)
    split = int(len(samples) * (1.0 - holdout))
    train = samples[:split]
    evaluate = samples[split:]
    meta = {"schema_version": SCHEMA_VERSION, "seed": seed}
    return (
        {**meta, "split": "train", "samples": train},
        {**meta, "split": "eval", "samples": evaluate},
    )


def write_dataset(directory: str | Path, **kwargs) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    train, evaluate = generate_dataset(**kwargs)
    train_path = directory / "training_data.json"
    eval_path = directory / "evaluation_data.json"
    train_path.write_text(json.dumps(train, indent=2), encoding="utf-8")
    eval_path.write_text(json.dumps(evaluate, indent=2), encoding="utf-8")
    return train_path, eval_path


def load_samples(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return list(payload.get("samples") or [])
