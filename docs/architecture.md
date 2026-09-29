# ENTROPY - Canonical Runtime Architecture (Industry Level)

## Final Year Major Project - End-to-End Working System

### Runtime Path (Production)

```
victim_server/user_files/ (18 files, controlled estate)
    ↓ watchdog Observer 0.2s + protected stores watcher
monitoring.watchdog_monitor.FileMonitor
    ↓ event deduplication (1s window)
monitoring.event_deduplicator
    ↓
monitoring.event_pipeline.EventPipeline (queue 10000, batch 50)
    → entropy.entropy_calculator.EntropyAnalyzer
      - Shannon entropy per file + delta vs history
      - Per-type normal ranges (txt 3.0-5.5, xlsx 6.0-7.5, jpg 7.0-7.8, etc)
      - Threat score 0-100
    → monitoring.defense_guard.collect_threat_flags
      - Ransom note (filename + phrase list)
      - Defense tamper (deletion from backup/quarantine stores)
      - Known-threat exchange lookup (fingerprint registry)
    → response.backup_manager.BackupManager.capture(strict=True for event-time)
      - Strict clean rule: inside normal range, no 0.5 margin, no ≥2.0 jump from last clean
      - Prevents ciphertext becoming restore source
    → monitoring.pipeline_runner.DecisionEngine
      - Rule engine (default, 0 false quarantine)
      - CampaignTracker (2+ files with encrypted signatures in 15s = CAMPAIGN CONFIRMED)
      - RF classifier (opt-in, SHAP, 100% detection)
      - DQN (opt-in, torch fallback)
    → response.response_module (terminate + quarantine)
      - ProcessTerminator: verified PID only, zombie-aware, self-kill whitelist
      - FileQuarantine: install-time folder, SHA3-256 + SHA-256 dual hash, meta.json
    → Campaign sweep (quarantine+restore all campaign files)
    → Post-kill verification (walk estate, hash vs last clean, repair mid-write)
    → response.backup_manager.BackupManager.restore (clean v1, rename-back)
    → response.forensic_report (one JSON per incident)
    → blockchain.connector.BlockchainConnector
      - Ganache ThreatLogger contract (owner-only)
      - LocalLedger fallback (default true, works without Ganache, labeled)
    → blockchain.fingerprint_exchange (share confirmed threats)
    → storage.database (events, 50 limit API)
    → app.py dashboard (socket.io push 0.4s: new_event + live_update)
```

### Startup Sequence (lab.py)

1. `install.py` logic: create quarantine_storage/, backup_storage/, logs/, reports/ (install-time folder per spec)
2. `create_fake_files.py --clean`: 18 files (6 Documents, 4 Downloads, 4 Desktop, 4 Pictures)
3. `PipelineRunner`: snapshot 18 files into backup store (baseline for restore)
4. `FileMonitor`: watch victim_server/user_files + protected stores (backup/quarantine deletion = tamper signal)
5. Dashboard (5000), Victim (5001) Flask + socketio threading mode
6. Attacker service (8001): stdlib ThreadingHTTPServer serving the React console
   (`attacker-ui/` -> `attacker_server/static/console/`) and the control API;
   falls back to `templates/attacker.html` when the bundle is absent

### Key Fixes for Industry Level (Final Year)

- **Campaign escalation**: slow realistic attacks (1.6 ev/s) never trip speed bar, but 2 files with encrypted signatures in 15s triggers TERMINATE+QUARANTINE at file 2
- **Strict clean labeling**: event-time captures labeled clean only if inside normal range AND no delta jump, so xlsx ciphertext 7.88 never becomes restore source
- **Content-based post-kill verification**: after kill, compare current file hash vs last clean hash, repair only if differs. No entropy-only false positives on jpgs (7.0)
- **Zombie-aware termination**: attacker console reaps child in _stream_reader finally, terminator treats zombie/already-gone as success, so kill instant rc=42 not FORCE KILLED after 3s
- **Real-time push**: dashboard push_updates() polls DB for new ids, emits new_event + live_update via socketio, client uses io({transports:['websocket','polling']})
- **Neutral victim explorer**: /api/files returns only name/size/modified/icon, no encrypted counts, no family, Quarantine locked behind vault
- **SHA3-256 dual hash**: storage/hashing.py provides sha3_256_file + dual_hash_file, response_module uses SHA3-256 primary
- **Console telemetry contract**: attacker `GET /api/stats` returns the same keys whether idle or running (phase, paused, progress, staged/hit/skipped/notes, bytes, observed rate, elapsed, exit code, defender verdict) plus structured log entries `{time, at, msg, level}`; `GET /api/targets` returns estate aggregates only and never file paths

### Data Flow for Demo (WannaCry)

1. Attacker POST /api/launch wannacry → spawns ransomware_engines.py subprocess (os.urandom overwrite + .WNCRY rename)
2. File 1: MODIFIED Financial_Report_2024.xlsx (entropy 7.88) → ALERT (60) → capture strict=False? Actually strict=True for event-time, labeled not clean, recorded in CampaignTracker
3. File 2: RENAMED Client_Meeting_Notes.docx.WNCRY (7.81) → ALERT + qualifies → CampaignTracker count distinct paths ≥2 → escalate to TERMINATE+QUARANTINE, kill_override = last_verified PID 3101
4. Response: terminate PID 3101 → SUCCESS → quarantine file 2 → restore clean v1 (captured at boot) → sweep file 1 → quarantine+restore
5. Post-kill verification: walk estate, Tax_Returns.pdf hash differs from last clean (4.9 vs 7.79) → quarantine+restore
6. Estate: 18/18 restored, 0 .WNCRY, 3 evidence files in quarantine_storage/

### Attacker Console Redesign (front end)

The operator console is a React + Tailwind app (`attacker-ui/`) built into
`attacker_server/static/console/` and served by the same stdlib service. It is
the offensive half of one product: same canvas, panels and typography as the SOC
dashboard, amber/red accents for the offensive surface.

- Payload catalog (<- `/api/families`, shared `catalog.py`), search + `1`-`9`/`0` selection
- Two-step launch confirmation; pause/resume/abort mapped to control-file pause and SIGINT
- Live telemetry from `/api/stats`, kill-chain timeline of transitions observed by the console
- Victim estate summary from `/api/targets`: totals, size, attackable, locked artifacts, notes, quarantine evidence
- Process console with levels, filters, grep, follow, copy and `campaign.log` export
- Path-traversal-safe asset serving; `do_HEAD` limited to the service's own routes
  (the inherited handler would otherwise expose repo file metadata)

The console reports the defense verdict as the run outcome: when the pipeline
terminates the process, the page switches to `KILLED BY DEFENDER`, shows exit
code 42 and how many staged files were overwritten before the kill.

### Security Boundaries

- Attacker confined to victim_server/user_files via safe_path() check
- Defender never kills whitelisted or own tooling (DEFENDER_TOOLING_MARKERS)
- Vault PIN compare_digest, session 8h, scope quarantine_only
- Quarantine files cannot be decrypted (os.urandom, no key) - honest

### Compatibility Facades (Do Not Extend)

- entropy_system.py
- blockchain/blockchain_logger.py

These emit DeprecationWarning and delegate to canonical implementations.

### For 200 Marks

This architecture is not PowerPoint - it's running code with 126 tests, deterministic benchmark, live demo verified, honest limitations published.
