# Week 03 — Aug 03-09, 2025: Decision Engine & Threat Scoring

## Objective
Build multi-signal threat engine that decides IGNORE/ALERT/TERMINATE/QUARANTINE with 0 false quarantine bar.

## Architecture
```
EntropyAnalyzer → DecisionEngine
    ↓
DecisionEngine.decide(event):
  - _base_decide(): per-file scoring
  - CampaignTracker: cross-file escalation (later week 9)
  - Returns action 0-3 + explanation
```

## Implementation Details

### 1. Rule-Based Engine (Default, 0 FQ Safety Bar)
**File**: `monitoring/pipeline_runner.py: DecisionEngine`

```python
def _base_decide(event):
    score = 0
    # Indicator 1: High entropy unknown type
    if entropy >= 6.8 and ext not in NORMAL_RANGES: score += 40
    # Indicator 2: Above normal for type
    if entropy > normal_max+0.5: score += 30
    # Indicator 3: Delta ≥2.0
    if abs(delta) >= 2.0: score += 25
    # Indicator 4: Extension changed
    if ext_changed: score += 20
    # Indicator 5: Speed ≥3.0/s
    if speed >= 3.0: score += 25
    # Action mapping
    if score >=70: return TERMINATE_QUARANTINE
    elif score >=40: return ALERT
    else: return IGNORE
```

### 2. Event Pipeline
**File**: `monitoring/event_pipeline.py`

- Queue size 10000, batch 50, dedup window 1.0s
- Entropy analysis worker thread
- Speed tracker (10s window)

### 3. Defense Signals
**File**: `monitoring/defense_guard.py`

- Ransom note: filename + phrase list (e.g., "restore my files", "decrypt")
- Defense tamper: deletion from backup_storage/ or quarantine_storage/
- Exchange lookup: fingerprint registry query

### 4. Engine Selection
**File**: `config.py: AI_ENGINE`

```python
AI_ENGINE = os.getenv("ENTROPY_AI_ENGINE", "auto").lower()
# auto/rules = deterministic rule engine (default, 0 FQ)
# rf = Random Forest (opt-in, 100% but 6 FQ)
# dqn = DQN (opt-in, torch optional, fallback to rules)
```

## Testing
```bash
python -m unittest tests.test_threat_signals -v
# Tests: per-file scoring, speed bonus, extension change
```

## Outcome
- Rule engine 0 false quarantines on legit workloads (critical safety)
- Per-file scores conservative (slow attacks score 60, not 70) - need campaign layer later
- Engine selection with fallback works

## Next Week
Response module: kill + quarantine + forensic reports
