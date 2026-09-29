# Week 08 — Sep 07-13, 2025: Benchmark & Recovery Drill

## Objective
Measure detection honestly with deterministic battery and full recovery loop.

## Architecture
```
benchmark/scenarios.py (8 attacks + 7 workloads, seeded random.Random)
    ↓
benchmark/runner.py (real DecisionEngine, fresh per scenario, SimClock)
    ↓
docs/benchmark-report.md (auto-generated, honest)
benchmark/recovery_drill.py (real baseline → attack → detection → quarantine → restore → byte compare)
    ↓
docs/recovery-drill-report.md
```

## Implementation Details

### 1. Attack Scenarios (8 variants)
**File**: `benchmark/scenarios.py`

- burst_encoder: speed + extension + range
- slow_crawler: extension + range only (no speed) — tests campaign layer
- polymorphic: randomized order, extensions, timing — 6/6 with campaign
- baseline_first: clean edit then encryption (delta)
- silent_unknown_ext: no prior history, unknown exts
- image_blindspot: in-range entropy, no rename — 0/6, documented blind spot
- note_dropper: ransom note is only signal (blind-spot payload) — note signal must catch
- backup_tamper: backup store deleted — defense tamper signal

Each run with and without startup baseline, across seeds

### 2. Legitimate Workloads (7, no baseline - harder FP case)
- document_editing, archive_creation, photo_import, video_write, git_burst (3/3 alerts, 0 FQ), csv_export, db_dump

### 3. Benchmark Runner - Real Engine
**File**: `benchmark/runner.py`

```python
def simulate_scenario(scenario, baseline=True, engine=None):
    if engine is None: engine = DecisionEngine(engine="rules")  # fresh per scenario
    else: engine.reset()  # prevent cross-contamination
    # Real detection chain: EntropyAnalyzer + DecisionEngine + 10s event-rate window simulated deterministically
    # Method text describes campaign layer + fresh engine
```

- Detection measured at file-event level: first op triggers alert or higher
- False quarantine = critical safety metric (legitimate file destroyed)
- Headline numbers auto-generated

### 4. Results (Final)
```
Attack detection: 42/48 (87.5%) rules, 48/48 (100%) RF
False quarantines: 0 rules, 6 RF (photo_import 3/3, video_write 3/3)
Known blind spots: image_blindspot
Federated: Known-threat recall 1/1 100%, single-sighting restraint 1/1 100%
```

### 5. Recovery Drill
**File**: `benchmark/recovery_drill.py`

- Real startup baseline → real attack replay → real detection → real quarantine → real restore
- Verifies estate byte-for-byte vs pre-attack, reports RTO (file ops and attacker-clock seconds) + recovery rate (recovered vs contained-but-not-restored vs lost)
- Result: 111/246 (45.1%) attacked files recovered, median RTO 8 ops with baseline
- Honest: no-baseline losses counted explicitly, not hidden

## Testing
```bash
python -m benchmark  # regenerates docs/benchmark-report.md + JSON
python -m benchmark.recovery_drill  # recovery-drill-report.md
python -m unittest tests.test_benchmark -v  # battery runs and reports
python -m unittest tests.test_recovery_drill -v
```

## Outcome
- Deterministic, regeneratable, honest numbers
- 0 false quarantines on rule engine (safety bar)
- Blind spot openly published

## Next Week
Campaign escalation - the major fix that makes slow attacks detectable
