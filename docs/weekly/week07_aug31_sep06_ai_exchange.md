# Week 07 — Aug 31-Sep 06, 2025: AI Classifiers & Federated Exchange

## Objective
Add explainable AI second classifier and cross-node threat memory.

## Architecture
```
DecisionEngine
  ├─ rules (default, 0 FQ)
  ├─ rf (Random Forest, SHAP, 100% detection, opt-in)
  └─ dqn (DQN, torch, opt-in, fallback to rules)

Event → fingerprint_exchange: query prior sightings → known threat auto-confirm if ≥2 independent nodes
```

## Implementation Details

### 1. Random Forest Second Classifier
**File**: `ai/rf_model.py`, `ai/train_rf.py`

```python
# Features (11):
# entropy_score, entropy_delta, files_per_sec, ext_changed, process_age_sec,
# is_signed, files_affected, avg_entropy_hist, is_known_process, time_hour, in_normal_range

# Training: 600 samples (298 attack), 200 eval, deterministic seed
# Eval: accuracy 1.0, AUC 1.0, well calibrated attack=0.9879 normal=0.0134
# Top features: in_normal_range=0.3597, entropy_delta=0.2812, process_age_sec=0.1299

# Save: ai/rf_weights.json (373K), datasets in data/training/rf_*.json
# SHAP per-incident explanations, fallback to global importances
```

- Measured on benchmark: 48/48 (100%) detection, closes image blind spot, but 6 FQ on photo/video import → opt-in `ENTROPY_AI_ENGINE=rf`, not default
- Rule engine keeps 0-FQ bar for production defender

### 2. DQN - Optional
**File**: `ai/dqn_model.py`

- QNetwork: Input 10 → Dense 128 ReLU Dropout → 64 → 32 → Output 4 (Q-values)
- ReplayBuffer 10000, epsilon greedy, target network update every 10 steps
- Fallback: `DQN unavailable (No module named 'torch') — using rule-based fallback` if torch missing
- Checkpoint atomic save via tempfile + os.replace

### 3. Federated Threat-Fingerprint Exchange
**File**: `blockchain/fingerprint_exchange.py`, `benchmark/exchange_simulation.py`

```python
# Shared registry: blockchain/exchange.db SQLite
# Every confirmed threat's SHA-256 written to registry
# Query on every event with content hash
# Fingerprint seen by ≥ EXCHANGE_CONFIRM_THRESHOLD (2) independent nodes = known threat auto-confirm
# Single node's sighting only corroborates (+25 score) never auto-quarantine — poison-node defence

# Simulation: 4 tenants share one registry, drive real decision + response chain
# Known-threat recall at first sight (confirmed, auto-quarantine) 1/1 100%
# Single-sighting restraint (recognised, NOT over-quarantined) 1/1 100%
```

- In lab, network is one SQLite file opened by several simulated nodes
- Multi-node simulation: `python -m benchmark.exchange_simulation`

## Testing
```bash
python -m ai.train_rf  # train + persist
python -m unittest tests.test_rf_classifier -v  # 13 tests
python -m unittest tests.test_fingerprint_exchange -v
python -m benchmark.exchange_simulation  # federated exchange
```

## Outcome
- RF second classifier works, SHAP explainable, 100% detection but honest about 6 FQ
- DQN optional with safe fallback
- Exchange simulation 100% recall, poison-node defence

## Next Week
Benchmark battery and recovery drill
