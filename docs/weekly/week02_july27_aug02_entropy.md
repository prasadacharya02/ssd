# Week 02 — July 27-Aug 02, 2025: Entropy Fingerprinting Engine

## Objective
Implement Shannon entropy analysis — core fingerprint that ransomware cannot hide.

## Architecture
```
FileMonitor (watchdog) → EntropyAnalyzer
    ↓
entropy.entropy_calculator.EntropyAnalyzer
    - Shannon entropy per file
    - Entropy delta vs history
    - Per-type normal ranges
    - Threat score 0-100
```

## Implementation Details

### 1. Shannon Entropy Calculation
**File**: `entropy/entropy_calculator.py:40-120`

```python
def _file_entropy_sample(file_path, sample_size=65536):
    counts = {}
    with open(file_path, 'rb') as f:
        data = f.read(sample_size)
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1
    total = len(data)
    return -sum((c/total) * log2(c/total) for c in counts.values())
```

- Normal txt: 3.4-4.2 bits/byte
- Encrypted: 7.8-8.0 (ceiling)
- Sample size 65536 bytes for performance

### 2. Per-Type Normal Ranges
**File**: `config.py:251-257`

```python
NORMAL_ENTROPY_RANGES = {
    ".txt": (3.0, 5.5), ".docx": (6.0, 7.5), ".pdf": (6.5, 7.8),
    ".jpg": (7.0, 7.8), ".zip": (7.5, 8.0), ".xlsx": (6.0, 7.5), ...
}
```

- Photo 7.8 stays quiet, txt 7.8 triggers
- 0.5 margin for measurement noise (later made strict for restore)

### 3. Threat Indicators
- Absolute entropy ≥6.8 (unknown types)
- Entropy above normal for file type (known types, > normal_max+0.5)
- Entropy delta ≥2.0 vs history
- Extension changed (disguise .WNCRY)
- Speed ≥3.0 files/sec (10s window)

### 4. Continuous Monitoring
**File**: `monitoring/watchdog_monitor.py:20-30`

```python
from watchdog.observers.polling import PollingObserver as Observer
self.observer = Observer(timeout=0.2)  # 0.2s polling, prevents Win32 handle freeze
```

- Watches victim_server/user_files recursively
- Watches protected stores backup_storage/ and quarantine_storage/ for DELETIONS only (tamper signal)
- Event types: CREATED, MODIFIED, DELETED, RENAMED

## Testing
```bash
python -m unittest tests.test_entropy -v
# Tests: high entropy detection, delta, normal ranges
```

## Outcome
- Entropy analyzer measures 3.4-8.0 range correctly
- Per-type ranges prevent false positives on jpgs
- Watchdog monitors continuously with 0.2s polling

## Next Week
Decision engine and threat scoring
