# ============================================================
# ENTROPY - Random Forest training
# python -m ai.train_rf
#
# Trains the second classifier on the versioned, seeded synthetic
# dataset and persists ai/rf_weights.json (+ the dataset under
# data/training/). Deterministic: the same seed reproduces the
# same model and metrics.
# ============================================================

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from ai import rf_model


def main() -> int:
    if not rf_model._SKLEARN_AVAILABLE:
        print("scikit-learn is not installed — cannot train "
              "(pip install -r requirements.txt)")
        return 1

    train, evaluate = rf_model.generate_dataset(seed=1337)
    os.makedirs(config.TRAINING_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.TRAINING_DATA_DIR, "rf_training_data.json"),
              "w", encoding="utf-8") as fh:
        json.dump(train, fh, indent=2)
    with open(os.path.join(config.TRAINING_DATA_DIR, "rf_evaluation_data.json"),
              "w", encoding="utf-8") as fh:
        json.dump(evaluate, fh, indent=2)

    model, metrics = rf_model.train_rf(train["samples"], evaluate["samples"])
    model_path = os.path.join(config.AI_DIR, "rf_weights.json")
    rf_model.save_model(model, metrics, model_path)

    print("Random Forest second classifier trained")
    print(f"  train samples : {metrics['n_train']} "
          f"({metrics['pos_train']} attack)")
    ev = metrics.get("eval") or {}
    if ev:
        print(f"  eval samples  : {ev['n']}")
        print(f"  eval accuracy : {ev.get('accuracy')}")
        print(f"  eval AUC      : {ev.get('auc')}")
        print(f"  mean proba    : attack={ev.get('mean_proba_attack')} "
              f"normal={ev.get('mean_proba_normal')} "
              f"(well calibrated ⇒ well separated)")
    print("  top features  : " + ", ".join(
        f"{k}={v}" for k, v in
        list(metrics["feature_importances"].items())[:5]
    ))
    print(f"  saved         : {model_path}")
    print(f"  datasets      : {config.TRAINING_DATA_DIR}/rf_*.json")
    print("  SHAP available:", rf_model._SHAP_AVAILABLE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
