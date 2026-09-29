# Week 01 — July 20-26, 2025: Project Setup & Install-Time Quarantine

## Objective
Initialize final year major project structure, meet core spec: quarantine folder created by user at install.

## Architecture Implemented
```
ROOT/
├── config.py (QUARANTINE_DIR, BACKUP_DIR, WATCH_FOLDERS)
├── victim_server/user_files/ (18 files: Documents/Downloads/Desktop/Pictures)
├── quarantine_storage/ (install-time, PIN locked)
├── backup_storage/ (versioned clean copies)
└── install.py (creates quarantine at install time)
```

## Implementation Details

### 1. Install-Time Quarantine Folder (SPEC REQUIREMENT)
**File**: `config.py:60-70`, `install.py:18-25`, `lab.py:45-55`

```python
# config.py
_quarantine_raw = os.getenv("ENTROPY_QUARANTINE_DIR", "").strip()
QUARANTINE_DIR = _resolve_path(_quarantine_raw) if _quarantine_raw else str(BASE_PATH / "quarantine_storage")
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# install.py
q_dir = Path(config.QUARANTINE_DIR)
q_dir.mkdir(parents=True, exist_ok=True)
print(f"Quarantine folder created by user at install: {q_dir}")
```

This satisfies: "file moved to quarantine folder created by user at install of the SOC software"

### 2. Victim Estate Fixtures
**File**: `victim_server/create_fake_files.py`

- 6 Documents (xlsx, docx, pdf), 4 Downloads, 4 Desktop txt, 4 Pictures jpg
- Deterministic seed, clean mode `--clean`
- Used for byte-for-byte verification: pristine copy in `/tmp/pristine`

```bash
python victim_server/create_fake_files.py --clean  # 18 files
```

### 3. Project Structure & Health Check
**File**: `main.py`

- Checks required modules: watchdog, psutil, numpy, flask, flask_socketio, dotenv
- Optional: torch, web3, eventlet, colorama with fallbacks
- Banner + version, exits non-zero if missing

## Testing
```bash
python main.py  # Environment ready
python install.py  # Quarantine folder created at install time
```

## Outcome
- Quarantine folder install-time creation verified
- 18 victim files created
- Project structure ready for monitoring

## Next Week
Entropy calculation and per-type normal ranges
