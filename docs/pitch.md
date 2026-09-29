# Ransomware Shield — Final Year Major Project Pitch (Industry Level, Honest)

> Every claim below is verifiable in code, tests, or `docs/benchmark-report.md`. No fake numbers.

## One-liner

**We catch ransomware by its unavoidable fingerprint — randomness — and recover data automatically before crisis. Kill at file 2, restore 18/18, zero false quarantines.**

## What It Is

End-to-end ransomware defense lab: real-time entropy monitoring, multi-signal threat engine with campaign escalation, verified containment, automatic recovery from clean backups, forensic reports, auditable ledger.

Ships as one-command lab: SOC dashboard (5000), attacker console (8001), victim explorer (5001).

## The Core Idea

Ransomware must scramble file data. Scrambling is measurable:

- Normal txt: 3.4-4.2 bits/byte
- Encrypted: 7.8-8.0 (ceiling)

We compare each file against its own history + file-type normal range. A 7.8-bit photo stays quiet, a 7.8-bit "photo" that was txt 5s ago triggers response.

## How It Works (Industry Level)

1. **Monitor** - watchdog 0.2s polling, entropy per file, event rate, extension change, startup baseline snapshot (18 files)

2. **Detection Engine** - multi-signal 0-100 score:
   - Absolute entropy vs per-type range (xlsx 6.0-7.5, jpg 7.0-7.8, etc)
   - Entropy delta vs own history (≥2.0 = suspicious)
   - Bulk speed (10s window, ≥3.0/s = suspicious)
   - Extension change (disguise .WNCRY)
   - Hard-confirmation: ransom note filename/phrase, defense tamper (deletion from backup/quarantine stores)
   - **Campaign escalation (NEW)**: 2+ distinct files with encrypted-data signatures in 15s = CAMPAIGN CONFIRMED, upgrade ALERT→TERMINATE even if per-file score conservative. This stops slow realistic attacks at file 2.

3. **Response**:
   - Terminate: only verified open-file PID, zombie-aware (reap in attacker console finally), self-kill whitelist (DEFENDER_TOOLING_MARKERS)
   - Quarantine: move to install-time folder `quarantine_storage/` (created by user at install), SHA3-256 + SHA-256 dual fingerprint, meta.json sidecar
   - Post-kill sweep: quarantine+restore all campaign files
   - Post-kill verification: walk estate, compare current hash vs last clean hash, repair mid-write files. Content signal, not entropy-only, so no false positives on jpgs.

4. **Recovery**:
   - BackupManager: versioned clean copies in `backup_storage/`, SHA-256 verified
   - Strict clean rule: event-time capture must be inside normal range (no 0.5 margin) AND no ≥2.0 jump from last clean. Office ciphertext 7.8-8.0 fails, never becomes restore source
   - Restore: quarantine → restore clean v1 → rename-back if needed. 18/18 byte-for-byte in live demo
   - We do NOT decrypt ransomware output (nobody can) - we restore pre-attack clean copy. Honest.

5. **Explainable AI**:
   - Rules default: 0 false quarantines (safety bar)
   - RF second classifier: calibrated 0-100 risk, SHAP per-incident, 48/48 detection (closes image blind spot) but 6 FQ on media, so opt-in `ENTROPY_AI_ENGINE=rf`
   - DQN: optional, torch, fallback to rules if missing

6. **Ledger + Audit**:
   - ThreatLogger Solidity contract on Ganache, with local SQLite fallback (default fallback=true, works without Ganache, clearly labeled mode)
   - Every incident: forensic report in `reports/` + ledger entry + exchange fingerprint

## Proof It Works (Live Demo Verified)

- **Live WannaCry**: hit 2/18 files, killed mid-file-3, rc=42 instant, 0 .WNCRY left, 18/18 restored (zip content hash + pdf byte compare)
- **Real-time push**: socket.io `new_event` +0.4s, `live_update` heartbeat, verified with raw frame parser
- **Neutral victim**: `/api/files` returns only name/size/modified, no encrypted counts, no family
- **Background auto-response**: quarantine BEFORE attack proceeds (campaign at file 2)

Benchmark battery: 8 attacks × baseline modes × seeds + 7 workloads, real DecisionEngine with campaign:

| Metric | Rules | RF |
|--------|-------|-----|
| Attack detection | 42/48 (87.5%) | 48/48 (100%) |
| False quarantines | 0 | 6 |
| Median ops to detect | 1-2 | 1 |
| Blind spot | image_blindspot (in-place high-entropy no rename) | none |

## Why 87.5% Not 100% (Honest Limitation)

`image_blindspot`: in-place encryption of jpg/mp4 without rename leaves entropy in normal range (7.0-7.8). No entropy-only detector can catch it. RF closes it via other features but breaks 0-FQ. Published openly.

## Quarantine Decryption (Honest)

Can privileged user decrypt quarantine? **No.** Attacker overwrites with `os.urandom()` + rename, no key. Quarantine holds ciphertext evidence for forensics. Recovery is via backup vault restore. Vault user `victim_user / 1234` can list, view metadata, forensic reports, but not decrypt. This is honest - real ransomware also not decryptable without attacker key.

## Install-Time Quarantine Folder (Spec Met)

`install.py` + `config.py` + `lab.py` all explicitly create `quarantine_storage/` at install time, log "Quarantine folder created by user at install". Operator can override via `ENTROPY_QUARANTINE_DIR`.

## Industry Level Highlights

- SHA3-256 + SHA-256 dual fingerprint (not just SHA-256)
- Campaign escalation (cross-file corroboration, stops slow attacks)
- Strict clean labeling (prevents ciphertext becoming restore source)
- Content-based post-kill verification (no entropy false positives)
- Zombie-aware termination (instant, not force-kill after 3s)
- Real-time socket.io push (sub-second, verified)
- Local ledger fallback (works without Ganache, labeled)
- 126 tests pass, 0 fail, deterministic benchmark

## For 200 Marks

This is not a PowerPoint project. It's a working system you can demo live, with honest numbers, no hidden failures, and clear limitations. Examiners can launch attack themselves and see kill+restore in real time.
