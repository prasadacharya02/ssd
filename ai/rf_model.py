# ============================================================
# ENTROPY - Random Forest second classifier
# ai/rf_model.py
#
# WHAT THIS IS:
# A calibrated, explainable 0-100 risk score produced by a Random
# Forest over the SAME feature vector the DQN uses (plus one feature
# the rule engine relies on: whether the entropy is normal for the
# file's extension). It is the "second-classifier layer" the pitch
# promises: a probabilistic, per-incident explainable score that
# sits alongside the deterministic rule engine.
#
# DESIGN NOTES (honest by construction):
# - Optional dependency: needs scikit-learn. If it is missing the
#   pipeline transparently falls back to the rule engine (exactly
#   like the optional DQN/torch path) — the pipeline never fails to
#   start. SHAP is a *further* optional: without it, explanations
#   fall back to the forest's global feature importances.
# - Deterministic: fixed random_state, seeded synthetic training
#   data (versioned schema, held-out eval split). Rerunning training
#   reproduces the same model and metrics.
# - The training data is SYNTHETIC and labelled as such in the model
#   metadata. It is a reasonable proxy for the detector's signals,
#   not a substitute for measured detection numbers (those come from
#   the benchmark battery, which drives the real decision chain).
# - Per-incident explanation: SHAP values name the top features that
#   pushed THIS decision up or down (e.g. "entropy_delta +, high
#   speed +, in-range-for-extension -").
# ============================================================

import base64
import io
import json
import os
import random
from datetime import datetime

import numpy as np

import config

# ── Optional dependencies (graceful fallback, like the DQN path) ──
try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    _SKLEARN_AVAILABLE = True
except Exception as _sk_err:           # pragma: no cover - env dependent
    joblib = None
    RandomForestClassifier = None
    _SKLEARN_AVAILABLE = False
    _SKLEARN_ERR = str(_sk_err)

try:
    import shap
    _SHAP_AVAILABLE = True
except Exception as _shap_err:         # pragma: no cover - env dependent
    shap = None
    _SHAP_AVAILABLE = False
    _SHAP_ERR = str(_shap_err)


# ── Feature schema (versioned) ─────────────────────────────────
# 10 features identical to the DQN state vector, plus
# "in_normal_range" — the signal the rule engine uses to keep
# high-entropy-but-legitimate files (photos, zips, video) quiet.
SCHEMA_VERSION = 2
FEATURES = (
    "entropy_score",      # 0.0 - 8.0
    "entropy_delta",      # -8.0 .. +8.0
    "files_per_sec",      # 0 - 50+
    "ext_changed",        # 0 / 1
    "process_age_sec",    # 0 - 3600+
    "is_signed",          # 0 / 1
    "files_affected",     # 0 - 200+
    "avg_entropy_hist",   # 0.0 - 8.0
    "is_known_process",   # 0 / 1
    "time_hour",          # 0 - 23
    "in_normal_range",    # 1.0 in-range / -1.0 out-of-range / 0.0 unknown ext
)

REQUIRED_FIELDS = FEATURES


def in_normal_range(ext: str, entropy: float) -> float:
    """+1.0 if the entropy is within the extension's normal range,
    -1.0 if the extension is known but the entropy is out of range,
    0.0 if the extension has no known range."""
    normal = config.NORMAL_ENTROPY_RANGES.get((ext or "").lower())
    if not normal:
        return 0.0
    return 1.0 if normal[0] <= entropy <= normal[1] else -1.0


def _hour_from_event(event: dict) -> float:
    ts = event.get("timestamp")
    if ts:
        try:
            return float(datetime.fromisoformat(str(ts)).hour)
        except (ValueError, TypeError):
            pass
    return 12.0


def extract_features(event: dict, avg_entropy_hist: float | None = None
                     ) -> list[float]:
    """Build the raw (un-normalised) 11-feature vector from a pipeline
    event. Mirrors the DQN FeatureExtractor semantics so both engines
    see the same signals; returns RAW values (the forest is trained on
    raw values)."""
    process = event.get("process") or {}
    entropy_score = float(event.get("entropy_overall") or 0.0)
    ext = (event.get("file_extension") or "").lower()

    proc_name = (process.get("name") or "").lower()
    whitelisted = [p.lower() for p in config.WHITELISTED_PROCESSES]
    is_signed = 1.0 if proc_name in whitelisted else 0.0
    is_known = is_signed

    if avg_entropy_hist is None:
        avg_entropy_hist = entropy_score

    return [
        entropy_score,                                        # 0
        float(event.get("entropy_delta") or 0.0),            # 1
        float(event.get("events_per_sec") or 0.0),           # 2
        1.0 if event.get("ext_changed") else 0.0,            # 3
        float(process.get("age_seconds") or 300.0),          # 4
        is_signed,                                            # 5
        float(event.get("events_in_window") or 1),           # 6
        float(avg_entropy_hist),                              # 7
        is_known,                                             # 8
        _hour_from_event(event),                              # 9
        in_normal_range(ext, entropy_score),                  # 10
    ]


# ── Synthetic, versioned training data ─────────────────────────
def _sample_ransomware(rng: random.Random) -> dict:
    """A ransomware event. Mixes burst + stealth, rename + in-place,
    fresh + persistent (compromised) processes, and (rarely) the
    in-range media blind spot.

    Feature semantics match the live pipeline: a renamed file appears
    at a NEW path (unknown extension → in_normal_range 0.0, extension
    changed); an in-place encryption keeps the extension (out of range
    unless it is the media blind spot)."""
    blind_spot = rng.random() < 0.15
    ext_changed = 1 if rng.random() < 0.6 else 0
    if ext_changed:
        in_range = 0.0          # new, unknown disguise extension
    else:
        in_range = 1.0 if blind_spot else -1.0
    return {
        "label": 1,
        "entropy_score": rng.uniform(6.8, 8.0),
        "entropy_delta": (rng.uniform(1.0, 6.0) if rng.random() < 0.7
                          else rng.uniform(0.0, 1.0)),
        "files_per_sec": (rng.uniform(3.0, 50.0) if rng.random() < 0.5
                          else rng.uniform(0.05, 3.0)),
        "ext_changed": ext_changed,
        # Mostly a freshly spawned tool, but sometimes a persistent
        # compromised process (a real attack is not always a newborn
        # process — the model must not lean on age alone).
        "process_age_sec": (rng.uniform(1, 300) if rng.random() < 0.7
                            else rng.uniform(300, 3600)),
        "is_signed": 0,
        "files_affected": (rng.randint(5, 200) if rng.random() < 0.7
                           else rng.randint(1, 5)),
        # History BEFORE this event: mostly the file was normal (low
        # history), sometimes it was already high-entropy.
        "avg_entropy_hist": (rng.uniform(3.0, 7.0) if rng.random() < 0.6
                             else rng.uniform(6.5, 8.0)),
        "is_known_process": 0,
        "time_hour": rng.randint(0, 23),
        "in_normal_range": in_range,
    }


def _sample_normal(rng: random.Random) -> dict:
    """A legitimate event. Four subtypes — the hard false-positive
    cases (high-entropy media, archives, fast-but-normal git bursts)
    are the majority of the challenge: high entropy/speed that is
    normal for the file type must NOT be ransomware."""
    kind = rng.choices(["text", "media", "archive", "git"],
                       weights=[40, 25, 20, 15])[0]
    base = {
        "label": 0,
        "is_signed": rng.choice([0, 1]),
        "is_known_process": rng.choice([0, 1]),
        "ext_changed": 0,
        "in_normal_range": 1.0,
    }
    if kind == "text":
        ent = rng.uniform(3.0, 5.5)
        base.update({
            "entropy_score": ent,
            "entropy_delta": rng.uniform(-0.4, 0.4),
            "files_per_sec": rng.uniform(0.01, 0.5),
            "process_age_sec": rng.uniform(300, 7200),
            "files_affected": rng.randint(1, 3),
            "avg_entropy_hist": ent + rng.uniform(-0.2, 0.2),
            "time_hour": rng.randint(8, 20),
        })
    elif kind == "media":
        ent = rng.uniform(6.5, 7.9)
        base.update({
            "entropy_score": ent,
            "entropy_delta": rng.uniform(-0.3, 0.3),
            "files_per_sec": rng.uniform(0.5, 5.0),
            "process_age_sec": rng.uniform(300, 7200),
            "files_affected": rng.randint(3, 20),
            "avg_entropy_hist": ent + rng.uniform(-0.2, 0.2),
            "time_hour": rng.randint(8, 20),
        })
    elif kind == "archive":
        ent = rng.uniform(7.4, 8.0)
        base.update({
            "entropy_score": ent,
            "entropy_delta": rng.uniform(0.0, 0.5),
            "files_per_sec": rng.uniform(0.1, 3.0),
            "process_age_sec": rng.uniform(300, 7200),
            "files_affected": rng.randint(1, 5),
            "avg_entropy_hist": ent + rng.uniform(-0.2, 0.2),
            "time_hour": rng.randint(8, 20),
        })
    else:  # git burst — fast, but normal content + known tool
        ent = rng.uniform(3.0, 6.0)
        base.update({
            "entropy_score": ent,
            "entropy_delta": rng.uniform(-0.3, 0.3),
            "files_per_sec": rng.uniform(3.0, 10.0),
            "process_age_sec": rng.uniform(60, 7200),
            "files_affected": rng.randint(5, 50),
            "avg_entropy_hist": ent + rng.uniform(-0.2, 0.2),
            "is_signed": 1,
            "is_known_process": 1,
            "time_hour": rng.randint(8, 22),
        })
    return base


def generate_dataset(*, seed: int = 1337, normal_count: int = 400,
                     ransomware_count: int = 400,
                     holdout: float = 0.25):
    """Deterministic (seeded) train/eval split. Returns
    (train_dict, eval_dict) each carrying schema metadata."""
    rng = random.Random(seed)
    samples = [_sample_normal(rng) for _ in range(normal_count)]
    samples.extend(_sample_ransomware(rng) for _ in range(ransomware_count))
    rng.shuffle(samples)
    split = int(len(samples) * (1.0 - holdout))
    train, evaluate = samples[:split], samples[split:]
    meta = {"schema_version": SCHEMA_VERSION, "seed": seed,
            "normal_count": normal_count,
            "ransomware_count": ransomware_count}
    return ({**meta, "split": "train", "samples": train},
            {**meta, "split": "eval", "samples": evaluate})


def validate_sample(sample: dict) -> bool:
    return (all(f in sample for f in REQUIRED_FIELDS)
            and sample["label"] in {0, 1})


def _to_matrix(samples: list[dict]):
    X = [[float(s[f]) for f in FEATURES] for s in samples]
    y = [int(s["label"]) for s in samples]
    return X, y


# ── Model persistence (JSON + base64 joblib) ───────────────────
def _model_to_bytes(model) -> bytes:
    buf = io.BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()


def _model_from_bytes(raw: bytes):
    return joblib.load(io.BytesIO(raw))


def train_rf(train_samples: list[dict], eval_samples: list[dict] | None = None,
             n_estimators: int = 200, min_samples_leaf: int = 2,
             random_state: int = 1337):
    """Train the forest on raw features; return (model, metrics)."""
    if not _SKLEARN_AVAILABLE:
        raise RuntimeError(
            "scikit-learn is required to train the Random Forest "
            f"({_SKLEARN_ERR})"
        )
    X, y = _to_matrix(train_samples)
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        n_jobs=1,          # deterministic
    )
    model.fit(X, y)

    metrics = {
        "n_train": len(y),
        "pos_train": int(sum(y)),
        "feature_importances": {
            f: round(float(v), 4)
            for f, v in sorted(zip(FEATURES, model.feature_importances_),
                               key=lambda kv: -kv[1])
        },
    }
    if eval_samples:
        Xv, yv = _to_matrix(eval_samples)
        proba = [float(p) for p in model.predict_proba(Xv)[:, 1]]
        pred = [1 if p >= 0.5 else 0 for p in proba]
        atk = [p for p, l in zip(proba, yv) if l == 1]
        nrm = [p for p, l in zip(proba, yv) if l == 0]
        metrics["eval"] = {
            "n": len(yv),
            "accuracy": round(float(accuracy_score(yv, pred)), 4),
            "auc": (round(float(roc_auc_score(yv, proba)), 4)
                    if len(set(yv)) > 1 else None),
            "mean_proba_attack": round(sum(atk) / len(atk), 4) if atk else None,
            "mean_proba_normal": round(sum(nrm) / len(nrm), 4) if nrm else None,
        }
    return model, metrics


def save_model(model, metrics: dict, path: str | os.PathLike) -> None:
    if not _SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is required to save the model")
    import sklearn
    payload = {
        "schema_version": SCHEMA_VERSION,
        "features": list(FEATURES),
        "label_column": "label",
        "model_b64": base64.b64encode(_model_to_bytes(model)).decode("ascii"),
        "training_metrics": metrics,
        "provenance": {
            "trained_on": "synthetic",
            "note": ("Training data is synthetic (seeded, versioned). "
                     "Measured detection/false-positive numbers come "
                     "from the benchmark battery, not this file."),
        },
        "sklearn_version": sklearn.__version__,
        "shap_available": _SHAP_AVAILABLE,
    }
    os.makedirs(os.path.dirname(os.path.abspath(str(path))), exist_ok=True)
    with open(str(path), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_model(path: str | os.PathLike):
    """Load + validate a saved forest. Returns (model, meta) or raises."""
    if not _SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is required to load the model")
    with open(str(path), "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Model schema {payload.get('schema_version')} != "
            f"expected {SCHEMA_VERSION}"
        )
    if tuple(payload.get("features") or ()) != FEATURES:
        raise ValueError("Model feature list does not match current schema")
    model = _model_from_bytes(base64.b64decode(payload["model_b64"]))
    return model, payload


# ── Live inference engine ──────────────────────────────────────
class RFEngine:
    """Loads a trained forest and scores live events, with a
    deterministic per-pid rolling entropy history (mirroring the DQN)."""

    TQ_THRESHOLD = 0.70     # risk >= 70 → terminate + quarantine
    ALERT_THRESHOLD = 0.40  # risk >= 40 → alert

    def __init__(self, model_path: str | os.PathLike | None = None):
        self.model_path = str(model_path or
                              os.path.join(config.AI_DIR, "rf_weights.json"))
        self.model, self.meta = load_model(self.model_path)
        self._entropy_history: dict[str, list[float]] = {}
        self._explainer = None            # lazy, cached TreeExplainer

    def _get_explainer(self):
        if self._explainer is None and _SHAP_AVAILABLE:
            self._explainer = shap.TreeExplainer(self.model)
        return self._explainer

    def _avg_history(self, pid: str, entropy: float) -> float:
        hist = self._entropy_history.setdefault(pid, [])
        hist.append(entropy)
        if len(hist) > 20:
            hist.pop(0)
        return sum(hist) / len(hist)

    def features(self, event: dict) -> list[float]:
        pid = str((event.get("process") or {}).get("pid") or "unknown")
        entropy = float(event.get("entropy_overall") or 0.0)
        avg = self._avg_history(pid, entropy)
        return extract_features(event, avg_entropy_hist=avg)

    @staticmethod
    def _shap_row(explainer, x_row: list[float]) -> np.ndarray:
        """Per-feature SHAP value for the ATTACK class (index 1),
        regardless of shap's return shape for binary classifiers."""
        sv = explainer.shap_values(np.array([x_row], dtype=float))
        if isinstance(sv, list):          # [class0 (n,f), class1 (n,f)]
            arr = np.asarray(sv[1])
        else:
            arr = np.asarray(sv)
        if arr.ndim == 3:                 # (n, f, 2) → attack class
            arr = arr[0, :, 1]
        elif arr.ndim == 2:               # (n, f) → single row
            arr = arr[0]
        return arr

    def _explain(self, x_row: list[float], proba: float) -> tuple[str, list]:
        """Return (explanation, top_features). SHAP local explanation
        when available, else the forest's global importances."""
        if _SHAP_AVAILABLE:
            try:
                explainer = self._get_explainer()
                vals = self._shap_row(explainer, x_row)
                order = sorted(range(len(FEATURES)),
                               key=lambda i: -abs(float(vals[i])))
                top = []
                for i in order[:3]:
                    v = float(vals[i])
                    top.append({
                        "feature": FEATURES[i],
                        "value": round(float(x_row[i]), 3),
                        "shap": round(v, 3),
                        "direction": "up" if v >= 0 else "down",
                    })
                drivers = ", ".join(
                    f"{t['feature']}{' +risk' if t['direction'] == 'up' else ' -risk'}"
                    for t in top
                )
                return (f"Random Forest (calibrated): risk "
                        f"{round(proba * 100)}% | drivers: {drivers}"), top
            except Exception:
                pass  # fall through to importances
        importances = (self.meta.get("training_metrics") or {}).get(
            "feature_importances", {})
        top = []
        for name, _imp in list(importances.items())[:3]:
            idx = FEATURES.index(name) if name in FEATURES else None
            top.append({
                "feature": name,
                "value": round(float(x_row[idx]), 3) if idx is not None else None,
                "shap": None,
                "direction": "up",
            })
        drivers = ", ".join(t["feature"] for t in top)
        return (f"Random Forest (calibrated): risk "
                f"{round(proba * 100)}% | top-importance features: {drivers}"), top

    def score(self, event: dict) -> dict:
        x = self.features(event)
        proba = float(self.model.predict_proba([x])[0, 1])
        risk = round(proba * 100.0, 1)
        if proba >= self.TQ_THRESHOLD:
            action = config.ACTION_TERMINATE_QUARANTINE
        elif proba >= self.ALERT_THRESHOLD:
            action = config.ACTION_ALERT
        else:
            action = config.ACTION_IGNORE
        explanation, top = self._explain(x, proba)
        return {
            "engine": "rf",
            "action": action,
            "probability": round(proba, 4),
            "risk": risk,
            "explanation": explanation,
            "top_features": top,
        }
