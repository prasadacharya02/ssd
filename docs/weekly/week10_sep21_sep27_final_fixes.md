# Week 10 — Sep 21-27, 2025: SHA3, Dependencies & Final Integration

## Objective
Fix remaining bugs that would fail in front of examiners: requirements conflict, blockchain fallback, SHA3 claim, RF version warning.

## Bugs Fixed

### 1. Requirements - ResolutionImpossible
**Bug**: `shap==0.51.0` depends on `numpy>=2` but pinned `numpy==1.26.4` → pip fails
```
ERROR: Cannot install ... shap 0.51.0 depends on numpy>=2
```

**Fix**: Compatible set verified in fresh venv:
```
watchdog==4.0.1
psutil==5.9.8
numpy==1.26.4
flask==3.0.2
flask-socketio==5.3.6
python-dotenv==1.0.1
colorama==0.4.6
scikit-learn==1.4.2  # was 1.9.1, requires numpy>=2
shap==0.44.0  # was 0.51.0, requires numpy>=2
web3==6.15.1
eventlet==0.35.2
torch==2.2.1
```
Now `pip install -r requirements.txt` works, `all deps ok`

### 2. Blockchain - No Connection
**Bug**: `BLOCKCHAIN_FALLBACK=False` default → Ganache offline = "No blockchain connection (fallback disabled)" → dashboard 0 tx, false claim

**Fix**: `config.py: BLOCKCHAIN_FALLBACK=True` default, `LocalLedger` fallback active, clearly labeled mode

Verified:
```
[BLOCKCHAIN] Ganache unreachable — using LOCAL LEDGER fallback ✅
Blockchain status: mode=fallback, tx_count=4, mode_label="Local SQLite ledger (not a blockchain)"
```

### 3. RF Model - Version Warning
**Bug**: Trained with sklearn 1.9.1, running 1.4.2 → warning "Trying to unpickle estimator from version 1.9.1"

**Fix**: Retrained `python -m ai.train_rf` → new `ai/rf_weights.json` 373K, 600 train, 200 eval, accuracy 1.0, AUC 1.0, top features in_normal_range=0.3597, entropy_delta=0.2812

### 4. SHA3 - False Claim
**Bug**: Pitch claimed SHA-3, code used only SHA-256

**Fix**: `storage/hashing.py`:
```python
def sha256_file(path): ... hashlib.sha256()
def sha3_256_file(path): ... hashlib.sha3_256()  # NEW
def dual_hash_file(path): ... both sha256 + sha3_256  # NEW
def sha256_bytes(data): ...
def sha3_256_bytes(data): ...

# response_module.py FingerprintGenerator
def generate_file_fingerprint(file_path):
    sha3 = hashlib.sha3_256()
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk: sha3.update(chunk); sha256.update(chunk)
    return sha3.hexdigest()  # primary SHA3-256
```

Now dual fingerprint SHA3-256 + SHA-256 for forensic integrity, industry standard true

### 5. Lab Launcher & Installer
**Fixes**:
- `lab.py`: correct URLs (was victim 8002, now 5001), install-time quarantine creation message, production banner, fallback true
- `install.py`: NEW file, explicitly creates quarantine_storage/ at install time per spec, logs "Quarantine folder created by user at install", creates backup vault, logs vault creds
- Fixed import bug `cannot import name 'create_fake_files'`

## Architecture Final

```
install.py (quarantine at install time)
    ↓
lab.py (4 services, 0.0.0.0, fallback true, DRY_RUN false)
    ├─ pipeline_runner (18 baseline, campaign, strict clean, post-kill verification)
    ├─ dashboard (5000, socket.io push 0.4s, fallback ledger)
    ├─ victim (5001, neutral, vault PIN)
    └─ attacker (8001, safe_path, 10 families, reap fix)
```

## Testing Final

```bash
python -m venv .venv && pip install -r requirements.txt  # works
python -m unittest discover -s tests  # 126 OK
python -m benchmark  # 42/48 0 FQ, slow_crawler 6/6, polymorphic 6/6
python -m benchmark.recovery_drill  # 45.1% honest
python main.py  # Environment ready
python install.py  # Quarantine folder created at install time
```

## Outcome
- No more ResolutionImpossible, no more "No blockchain connection", no more SHA3 false claim
- All dependencies work, all tests pass, live demo 18/18 restored
- Ready for final week integration

## Next Week
Final integration, live demo verification, docs finalization for 200 marks
