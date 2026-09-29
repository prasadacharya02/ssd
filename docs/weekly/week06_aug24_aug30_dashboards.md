# Week 06 — Aug 24-30, 2025: SOC, Victim, Attacker Dashboards

## Objective
Build 3 surfaces: SOC real-time feed, neutral victim explorer, attacker console. Meet spec: SOC continuously monitors, victim doesn't show attack details.

## Architecture
```
Pipeline (writes events to entropy.db)
    ↓
SOC Dashboard (5000): Flask + SocketIO threading, push_updates() every 0.4s
    - new_event push (full row)
    - live_update heartbeat (total/threats)
    ↓
Victim Explorer (5001): Flask, neutral, vault PIN
Attacker Console (8001): Flask, launch 10 families, safe_path confinement
```

## Implementation Details

### 1. SOC Dashboard - Continuous Monitoring
**File**: `app.py:349-408`, `monitoring/pipeline_runner.py:924`

```python
# pipeline_runner.py
[WATCHING RECURSIVE] victim_server/user_files
[WATCHING PROTECTED STORE] backup_storage
[WATCHING PROTECTED STORE] quarantine_storage
[OK] Pipeline is active
[RUNNER] Pipeline running — waiting for events...

# app.py
def push_updates():
    last_id = _last_event_id()
    while True:
        with app.app_context():
            db = get_db()
            new_rows = db.execute("SELECT * FROM events WHERE id > ? ORDER BY id LIMIT 100", (last_id,))
            for row in new_rows:
                socketio.emit("new_event", dict(row))  # sub-second push
                last_id = row["id"]
            stat = db.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN action>=1 THEN 1 ELSE 0 END) AS threats FROM events").fetchone()
            socketio.emit("live_update", {total, threats, time})
        time.sleep(0.4)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
```

- Verified with raw socket.io frame parser: CREATED push +0.4s, DELETED +0.4s, 42 frames in 15s
- API: /api/stats, /api/events (50 limit), /api/entropy, /api/alerts, /api/blockchain/status, /api/quarantine, /api/backup, /api/reports

### 2. Victim Explorer - Neutral & Structured
**File**: `victim_server/app.py`

```python
ALLOWED_FOLDERS = {"Documents", "Downloads", "Desktop", "Pictures", "Quarantine"}

def get_file_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".docx",".doc"): return "doc"
    if ext in (".xlsx",".xls"): return "xls"
    # Unknown extensions (including attacker renamed) → generic icon
    # Explorer never labels file as encrypted - detection in SOC

@app.route("/api/folders")
def get_folders():
    # Neutral stats: item count + total size, no attack intel
    # Quarantine locked behind vault
    if folder=="Quarantine" and not _vault_unlocked():
        return {"name":"Quarantine","file_count":actual_count,"size":"🔒 Locked","locked":True}

@app.route("/api/files/<folder>")
def get_files(folder):
    # Only name/size/modified/icon, no encrypted counts, no family
    if folder=="Quarantine" and not _vault_unlocked():
        return {"error":"privileged_access_required"}, 403
```

- Structure: This PC with 5 folders, each file_count + size, files with name/size/modified
- Vault: `victim_user / 1234`, session 8h, scope quarantine_only, `compare_digest` for PIN
- Real file explorer can't show "encrypted by WannaCry" - SOC does

### 3. Attacker Console - Safe
**File**: `attacker_server/app.py`, `ransomware_engines.py`

```python
def safe_path(path):
    candidate = Path(path).resolve()
    candidate.relative_to(_victim_root())  # must stay inside victim_server/user_files
    return candidate

class WannaCryEngine:
    extension = ".WNCRY"
    def modify_file(file_path):
        with file_path.open("wb") as handle:
            handle.write(os.urandom(max(original_size, 1024)))  # no key, original destroyed
        Path(file_path).rename(new_path)  # + .WNCRY
```

- 10 families: wannacry, ryuk, maze, revil, blackcat, alphv, akira, clop, qilin, lockbit5
- Control token `entropy-lab` for POST /api/launch, safe_path confinement
- Reaps child in _stream_reader finally (fixes zombie)

### 4. Lab Launcher
**File**: `lab.py`

- _ensure_quarantine(): creates quarantine_storage/, backup_storage/, logs/, reports/ at install time, logs "Quarantine folder created by user at install"
- Starts 4 services: pipeline, dashboard, victim, attacker
- Env: ENTROPY_WATCH_FOLDERS=victim_server/user_files, DRY_RUN=false, CONTROL_TOKEN=entropy-lab, BLOCKCHAIN_FALLBACK=true

## Testing
```bash
curl http://127.0.0.1:5000/api/stats  # SOC
curl http://127.0.0.1:5001/api/folders  # Victim: Documents 6, Downloads 4, Desktop 4, Pictures 4, Quarantine 0 locked
python -m unittest tests.test_service_integration -v
```

## Outcome
- SOC continuously monitors file changes, shows all events in real time via socket.io push
- Victim works like real file explorer, structured, neutral, vault PIN protected
- Attacker confined, safe for lab

## Next Week
RF classifier, DQN, federated exchange
