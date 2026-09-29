# Week 09 — Sep 14-20, 2025: Campaign Escalation & Critical Bug Fixes

## Objective
Fix the no-kill bug at realistic attack speed and restore bug that put ciphertext back as clean version. This week makes demo actually work end-to-end.

## Problem Found

**Bug 1 - No Kill at Realistic Speed:**
- 1× WannaCry = 1.6-2.1 ev/s < 3.0 threshold → no +25 speed bonus
- Deltas ~0.9-1.0 <2.0 → per-file max 60 <70 → kill only on last txt file (score 70)
- Demo would show attack encrypting all 18 files before kill

**Bug 2 - Restore Ciphertext as Clean:**
- Backup captures taken mid-attack labeled ransomware content (7.8-8.0) as clean because xlsx normal range 6.0-7.5 +0.5 margin covers it
- Restore then put encryption back under original name
- Live log: `RESTORED: ... H=7.89` = ciphertext entropy

**Bug 3 - File Being Written at Kill Escapes:**
- File being encrypted when killed generated no alert (score 30 <40) → ciphertext left on disk

**Bug 4 - 3s FORCE KILLED:**
- Child exits instantly on SIGTERM (verified isolated test pid 2314)
- psutil waiter in pipeline is NOT parent (Flask console is parent), exited child lingers as zombie until console reaps → non-parent wait polls, times out, SIGKILL no-op

## Architecture Fix

```
CampaignTracker (new class before DecisionEngine)
    ↓
DecisionEngine.decide() = campaign layer over _base_decide()
    - _qualifies(event): entropy_overall ≥6.8 AND (abs(delta)≥2.0 OR ext_changed)
    - check_and_record: count distinct paths with action≥ALERT ≥ CAMPAIGN_MIN_FILES-1
    - On escalate: action<3→3, campaign=True, sweep_events, kill_override=last_verified PID
    ↓
_on_analyzed_event: kill_override → event["process"] when action≥TERMINATE and own process unverified
    ↓
Post-response sweep: quarantine+restore all campaign files
Post-kill verification: walk estate, hash vs last clean, repair mid-write files (content signal, not entropy)
```

## Implementation Details

### 1. CampaignTracker
**File**: `monitoring/pipeline_runner.py: CampaignTracker`

```python
class CampaignTracker:
    entries = deque((wall_ts, normpath, event, action)) pruned by CAMPAIGN_WINDOW_SECONDS (15.0)
    last_verified = (wall_ts, proc) tracked separately
    _qualifies(event): entropy_overall ≥6.8 AND (abs(delta)≥2.0 OR ext_changed)
    _verified_process: needs identity_verified+pid, skips DEFENDER_TOOLING_MARKERS
    check_and_record(event, action) -> (escalate, sweep, kill_override):
        records qualifying events
        escalate = action≥ALERT and count(other distinct paths with action≥ALERT) ≥ CAMPAIGN_MIN_FILES-1 (2)
        sweep = dict-copies of other alert+ campaign events whose file still exists
        kill_override = None if own process verified else last_verified[1]

class DecisionEngine(engine=None, campaign=None→config.CAMPAIGN_ENABLED=True):
    def decide():
        decision = _base_decide()
        escalate, sweep, kill_override = campaign_tracker.check_and_record(event, action)
        if escalate and action<3: action=3, explanation="CAMPAIGN CONFIRMED: N files with encrypted-data signatures in 15s | prior"
```

- Env: ENTROPY_CAMPAIGN_ENABLED, ENTROPY_CAMPAIGN_WINDOW_SECONDS, ENTROPY_CAMPAIGN_MIN_FILES
- FQ safety: no legit workload qualifies (git_burst entropy <6.8, archive/photo/video delta 0 + no ext change)

### 2. Strict Clean Labeling
**File**: `response/backup_manager.py: _is_clean(strict=True)`

```python
def _is_clean(file_path, entropy, strict=False, last_clean_entropy=None):
    if not strict:
        if normal: return entropy <= normal[1] + 0.5
        return entropy < 6.8
    if normal is None: return False  # unknown type at event time = not clean
    if entropy > normal[1]: return False  # no margin
    if abs(entropy - last_clean_entropy) >= 2.0: return False  # no delta jump
    return True

def capture(file_path, event, strict=False):
    with lock:
        manifest = _load_manifest()
        last_clean_entropy = find last clean
        clean = _is_clean(..., strict, last_clean_entropy)  # atomic
        digest = _store_blob(file_path)
```

- Fixes: xlsx 7.88, docx 7.83, pdf 7.79 no longer labeled clean
- Label computed atomically against manifest

### 3. Post-Kill Verification - Content-Based
**File**: `monitoring/pipeline_runner.py: _post_kill_verification()`

```python
def _post_kill_verification():
    # Walk protected estate once after confirmed campaign kill
    # Repair signal is CONTENT not entropy level
    for root_dir in WATCH_FOLDERS:
        for path in walk:
            candidate = backup.find_restore_candidate(path)
            if candidate is None: continue
            current_sha = sha256_file(path)
            if current_sha == candidate["sha256"]: continue  # identical to last clean
            # Content differs from last clean → quarantine+restore
            event = {file_path, entropy, SWEEP, ...}
            execute_response(TERMINATE_QUARANTINE, event, ...)
            repaired +=1
            # Re-prime entropy history with restored clean content
```

- Fixes: Tax_Returns.pdf mid-write repaired, no false positives on jpgs (7.0 entropy but hash same as clean)

### 4. Zombie Reap Fix
**File**: `attacker_server/app.py: _stream_reader`, `response/response_module.py: terminate()`

```python
# attacker_server/app.py
def _stream_reader():
    try: ... 
    finally: proc.wait(timeout=10)  # reap child when stdout pipe closes

# response_module.py
except TimeoutExpired:
    if proc.status() == STATUS_ZOMBIE: success "terminated (awaiting reap)"
    if NoSuchProcess/AccessDenied from status(): "already gone"
    else: force kill
```

- Kill now instant rc=42 SUCCESS, not FORCE KILLED after 3s

## Live Verification (Final)

```
Phase: KILLED_BY_DEFENDER hit=2/18 defender_killed=True rc=42
[KILL] Using campaign-verified process PID:3101
[THREAT] Client_Meeting_Notes.docx.WNCRY H=7.81 → QUARANTINED → RESTORED clean v1
[SWEEP] Financial_Report_2024.xlsx.WNCRY → QUARANTINED+RESTORED
[SWEEP] Post-kill verification scan ...
[SWEEP] Tax_Returns.pdf: content differs from last clean version (H=7.79) → quarantining + restoring
[SWEEP] Post-kill verification complete: 1 file(s) repaired
.WNCRY left: 0 | quarantine: 3 evidence | ALL 18 FILES MATCH PRE-ATTACK
```

## Testing
```bash
python -m unittest discover -s tests  # 126 pass, 1 fail expected (baseline upgrades alerts to quarantine) → fixed with 3 new campaign tests
python -m benchmark  # slow_crawler 6/6 quarantined (was 0/6), polymorphic 6/6
```

## Outcome
- Demo now works end-to-end: kill at file 2, 18/18 restored, no false positives
- Campaign escalation is what stops slow realistic attacks
- This week is the core industry-level innovation

## Next Week
SHA3, requirements, final integration
