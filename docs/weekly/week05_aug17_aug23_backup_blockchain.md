# Week 05 — Aug 17-23, 2025: Backup Vault & Blockchain Audit

## Objective
Implement recovery via clean backup restore (not decryption) and auditable ledger.

## Architecture
```
File Event → BackupManager.capture()
    ↓
backup_storage/manifest.json (versioned, SHA-256 verified)
    ↓
On TERMINATE_QUARANTINE: BackupManager.restore() → clean v1 + rename-back
    ↓
BlockchainConnector → Ganache ThreatLogger OR LocalLedger fallback
```

## Implementation Details

### 1. Backup Manager - Strict Clean Rule
**File**: `response/backup_manager.py`

```python
def _is_clean(file_path, entropy, strict=False, last_clean_entropy=None):
    if not strict:
        if normal: return entropy <= normal[1] + 0.5  # lenient for baseline
        return entropy < 6.8
    # Strict for event-time captures:
    if normal is None: return False  # unknown type at event time = not clean
    if entropy > normal[1]: return False  # no margin
    if abs(entropy - last_clean_entropy) >= 2.0: return False  # no delta jump
    return True

def capture(file_path, event, strict=False):
    with lock:
        manifest = _load_manifest()
        last_clean_entropy = find last clean version's entropy
        clean = _is_clean(file_path, entropy, strict, last_clean_entropy)
        digest = _store_blob(file_path)  # SHA-256
        versions.append({version, sha256, entropy, clean, captured_at})
        if len(versions) > max_versions: evict oldest
```

- Fixes major bug: office ciphertext 7.8-8.0 was inside lenient range +0.5 → labeled clean → restore put ciphertext back. Strict rule prevents.
- Capture atomic against manifest (fixes race)
- Restore candidate: latest clean version before threat, blob must verify SHA-256

### 2. Blockchain Connector - Fallback Fix
**File**: `blockchain/connector.py`, `config.py`

```python
# config.py
BLOCKCHAIN_FALLBACK = _env_bool("ENTROPY_BLOCKCHAIN_FALLBACK", True)  # was False, now True

# connector.py
class LocalLedger:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        CREATE TABLE ledger (id, fingerprint, threatType, timestamp, pid, entropy, ...)
    def add(event): INSERT INTO ledger ...
    def count(): SELECT COUNT(*) ...

class BlockchainConnector:
    def _connect():
        if _try_ganache(): mode=ganache
        elif config.BLOCKCHAIN_FALLBACK: fallback=LocalLedger(...), mode=fallback
        else: mode=none
```

- Fixes bug: Ganache offline + fallback disabled = "No blockchain connection" → 0 tx, false claim
- Now fallback enabled by default, works without Ganache, clearly labeled `mode_label: Local SQLite ledger (not a blockchain)`

### 3. Recovery - Honest
**File**: `docs/limitations.md`

- Does NOT decrypt ransomware files — key held by attacker, no product can
- Recovery = restoring known-good copy captured BEFORE attack
- Renamed file restored then renamed back when original path free
- Files only ever existed encrypted not restorable

## Testing
```bash
python -m unittest tests.test_backup_restore -v
# Tests: clean labeling, restore candidate, SHA verification
```

## Outcome
- Backup vault versioned, SHA verified, strict rule prevents dirty restore
- Blockchain fallback works, 4 tx in live demo
- Recovery honest, not decryption

## Next Week
SOC dashboard, victim explorer, attacker console
