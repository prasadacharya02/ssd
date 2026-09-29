# Week 04 — Aug 10-16, 2025: Response Module & Safety

## Objective
Implement verified containment: kill process + quarantine file + forensic reports, with safety gates to never kill own software.

## Architecture
```
DecisionEngine → ResponseModule.respond()
    ↓
ProcessTerminator (psutil, verified PID only)
FileQuarantine (install-time folder, SHA3-256)
Forensic Report (JSON per incident)
Blockchain Logger (queue, background thread)
```

## Implementation Details

### 1. Process Terminator - Safety First
**File**: `response/response_module.py: ProcessTerminator`

```python
def terminate(pid, process_name, expected_create_time):
    # Safety 1: Don't kill own PID
    if pid == our_pid: return Refused
    # Safety 2: Don't kill system PID <10
    if pid < 10: return Refused
    # Safety 3: Whitelisted (System, svchost.exe, etc)
    if process_name.lower() in whitelist: return Refused
    # Safety 4: Re-read identity before kill (prevent PID reuse)
    actual_name = proc.name()
    if actual_name.lower() != process_name.lower(): return Refused
    # Safety 5: Never kill own tooling (DEFENDER_TOOLING_MARKERS)
    cmdline = " ".join(proc.cmdline()).lower()
    for marker in DEFENDER_TOOLING_MARKERS:
        if marker in cmdline: return Refused
    proc.terminate()
    proc.wait(timeout=3)
    # Zombie-aware: if status==ZOMBIE → success (awaiting reap)
```

- Fixes 3s FORCE KILLED bug: child exits instantly on SIGTERM, but parent (attacker console) hasn't reaped → zombie. Non-parent waiter times out. Fixed by reap in _stream_reader finally + zombie check.

### 2. File Quarantine - Install-Time Folder
**File**: `response/response_module.py: FileQuarantine`

```python
def quarantine(file_path, event):
    fingerprint = generate_file_fingerprint(file_path)  # SHA3-256
    short_hash = fingerprint[:12]
    quarantine_name = f"{short_hash}_{original_name}"  # e.g., bda2bdd3a772_Financial_Report_2024.xlsx.WNCRY
    shutil.move(file_path, quarantine_path)  # move to quarantine_storage/
    _save_metadata(quarantine_path, file_path, fingerprint, event)  # .meta.json sidecar
```

- Quarantine folder created at install time per spec
- Dual hash SHA3-256 + SHA-256 for forensic integrity
- Metadata: original_path, entropy, threat_score, process, timestamp

### 3. Fingerprint Generator - SHA3-256
**File**: `response/response_module.py: FingerprintGenerator`, `storage/hashing.py`

```python
def generate_file_fingerprint(file_path):
    sha3 = hashlib.sha3_256()
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            sha3.update(chunk)
            sha256.update(chunk)
    return sha3.hexdigest()  # primary SHA3-256
```

### 4. Forensic Reports
**File**: `response/forensic_report.py`

- One JSON per incident: evidence, decision, actions, audit references
- Stored in reports/ with timestamp

## Testing
```bash
python -m unittest tests.test_response_safety -v
# Tests: whitelisted not killed, own process not killed, incomplete identity refused
```

## Outcome
- Safety gates prevent self-kill
- Quarantine moves file to install-time folder BEFORE attack proceeds
- SHA3-256 fingerprint for blockchain

## Next Week
Backup manager and recovery
