# ENTROPY — Gap Analysis (honest, pre-demo audit)

Format per gap: **GAP → why it matters → current status → fix → implemented? →
how to demonstrate**. Generated from a code-level audit, not from the PPT.
Regenerate the verification evidence with `python verify_demo.py` (lab running).

---

## 1. Detection gaps

### 1.1 Unknown-extension in-place encryption without rename
- **Why it matters:** ransomware that encrypts files *in place* with
  never-before-seen extensions and no rename leaves no magic/extension ground
  truth to confirm against.
- **Status:** detected at ALERT level (entropy + chi² flatness) — never
  auto-quarantined on first sight, by design (chi² alone can be a legitimate
  new binary format). Campaign correlation (2+ suspicious files in 15 s) still
  escalates to containment.
- **Fix / implemented?** Accepted policy, not a bug. Extending hard quarantine
  here would break the 0-false-quarantine bar.
- **Demonstrate:** `attack_silent_unknown_ext` benchmark scenario:
  `python -m unittest tests.test_benchmark` — detection AND quarantine via
  campaign escalation.

### 1.2 Entropy sampled over the first 64 KiB
- **Why it matters:** an attacker encrypting only content *beyond* the sampled
  region of a very large file could keep sampled entropy low.
- **Status:** `ENTROPY_SAMPLE_SIZE_BYTES` (default 65536); section entropies +
  `chi2_tail` cover the tail of the *sample*, not the whole file.
- **Fix / implemented?** Not implemented: whole-file/multi-offset sampling
  trade-off (latency vs coverage). Realistic for the demo (fixtures ≤ 300 KB
  and ransomware engines overwrite from offset 0).
- **Demonstrate:** point examiners to `config.SAMPLE_SIZE_BYTES` and the
  section-entropy fields in any forensic report.

## 2. False-positive risks

### 2.1 Developer bursts (git operations) raise ALERTS
- **Why it matters:** an alert storm in a demo looks like crying wolf.
- **Status:** measured: 3/21 workload runs alert (`git_burst`) — ALERT only,
  NEVER quarantine. 0 false quarantines across all 7 benign workloads.
- **Fix / implemented?** Implemented: destructive actions require ≥2
  independent signals (entropy evidence + behavioural corroboration).
- **Demonstrate:** `python -m benchmark` — workload table shows 0 false
  quarantines; Section-31 FP tests map as: TEST 1 = `document_editing`,
  TEST 2 = `db_dump`/`video_write`, TEST 3 = `archive_creation`/`photo_import`,
  TEST 4/5 = `wannacry` live / `burst_encoder`+`polymorphic` battery.

### 2.2 Fixture realism (WAS a real defect — FIXED)
- **Why it mattered:** victim fixtures stamped a PNG magic inside `.jpg`/`.zip`
  files; every estate RESET looked like a ransomware campaign on the SOC.
- **Status:** FIXED. Fixtures now carry valid per-extension magic
  (`JPEG SOI`, `PK\x03\x04`) with structured (non-uniform) bodies;
  `Report_Draft.docx` is now a real DOCX. Regression-pinned by
  `tests/test_fixture_generation.py::test_fixtures_have_valid_magic_for_their_extension`.
- **Demonstrate:** RESET the estate while watching the SOC feed: resets now
  produce IGNORE/ALERT rows only, zero self-quarantines (verified live:
  23 IGNORED / 1 ALERT / 0 self-quarantine since clean start).

## 3. False-negative risks

### 3.1 Magic-preserving partial encryption of large files
- **Why it matters:** keeping the first KiB intact preserves the magic header;
  if byte structure is also preserved, structural signals weaken.
- **Status:** mitigated by `chi2_tail` (last 20 KB of the sample) + section
  entropy deltas. Whole-file coverage remains the accepted limitation above.
- **Fix / implemented?** Partially implemented (tail chi²). Full fix future.

### 3.2 Slow-drip encryption below the rate threshold
- **Why it matters:** 1 file/30 s never trips speed signals.
- **Status:** single-file structural evidence (magic mismatch / flat chi² +
  rename) still quarantines on first sight — no speed required.
- **Demonstrate:** `attack_slow_crawler` in `python -m benchmark` → 6/6.

## 4. Backup / recovery weaknesses

### 4.1 Backup store is on the same disk, unencrypted
- **Why it matters:** an attacker with sufficient rights can delete
  `backup_storage/` — recovery would then be impossible.
- **Status:** deletion inside the protected store is a **hard-confirmation
  defense-tamper signal** (immediate incident) — detected, not prevented.
- **Fix / implemented?** Detect implemented; off-box/immutable copies are
  future work. The simulator *cannot* reach the store at all
  (`safe_path` sandbox limits it to `victim_server/user_files`) —
  demonstrated by `tests/test_simulator_safety.py` and `attack_backup_tamper`.

### 4.2 Restore could resurrect attacker content if mislabeled "clean"
- **Why it matters:** restoring ciphertext is worse than no restore.
- **Status:** prevented by the strict clean rule (in-range entropy AND no
  ≥2.0 jump from the last clean version) + restore candidates are
  SHA-256-verified; post-write hash verification on every restore.
- **Demonstrate:** `python -m unittest tests.test_backup_restore` (18 tests);
  `docs/recovery-drill-report.md` (8/8 with baseline per rename attack).

## 5. Race conditions

### 5.1 Kill lands mid-write on a not-yet-detected file
- **Status:** handled by the content-based post-kill verification sweep
  (hash vs last clean version — entropy level alone never triggers repair).
- **Demonstrate:** drill reports `Post-kill verification` in live runs;
  `tests/test_recovery_drill.py`.

### 5.2 Defender's own actions echo as new events
- **Status:** `defender_actions` registry filters restore/quarantine echoes;
  `[SELF]`-tagged log lines. Implemented.

### 5.3 PID reuse between attribution and kill
- **Status:** kill requires identity revalidation (name + PID + create_time)
  at termination time; stale identity → `TERMINATE_REFUSED`, quarantine still
  proceeds. Implemented (`response/response_module.py`,
  `tests/test_response_safety.py`).

## 6. Process identification problems

- **Status:** watchdog does not report *which* process wrote a file;
  attribution is verified via open-file handles at event time
  (`identity_verified`). If unobtainable → the process is never guessed and
  never killed; containment falls back to quarantine+restore.
- **Fix / implemented?** Implemented as a *safety gate*; kernel-level
  attribution (fanotify/ETW) is future work — do not claim kernel hooks in
  the viva.

## 7. File-monitoring limitations

- Watchdog polling latency ≈0.2 s; network shares not covered; the protected
  store watcher ignores its own manifest rewrites by name (evictions beyond
  `ENTROPY_BACKUP_MAX_VERSIONS` may raise benign tamper alerts — safe
  direction).

## 8. Blockchain failure scenarios

- **Ganache unreachable / web3 missing** → labeled SQLite fallback (mode is
  explicit in `/api/blockchain/status`; never faked as a chain). **Fallback is
  NOT immutable** — editable local DB; say this in the viva.
- **Ganache up, wrong wallet** → contract load fails → fallback + logged.
- **Writer crash mid-burst** → single queued writer thread, `flush()` at
  shutdown; failed TXs logged, pipeline continues.
- **In this sandbox:** Ganache is not installed, so the demo runs in fallback
  mode — on the exam laptop either start Ganache first (mode becomes
  `ganache`) or present the fallback honestly.

## 9. Database failure scenarios

- SQLite single-file (`entropy.db`); pipeline writes are serialized; dashboard
  opens short-lived connections per request. DB deleted at runtime → next
  write recreates schema (`init_db` idempotent); heartbeat row signals
  OFFLINE to the dashboard instead of silent staleness.

## 10. Dashboard synchronization issues

- **WAS real:** socket.io client from CDN + python-socketio 5.x rejecting
  `/socket.io/socket.io.js` → broken live channel; fixed with vendored local
  assets, regression-pinned by `tests/test_dashboard_realtime.py`.
- React SPA at `/` falls back to legacy template if the bundle is missing.
- Pipeline heartbeat (2 s) drives the OFFLINE/NOT-WATCHING/DRY-RUN banner —
  the dashboard cannot silently misrepresent a dead pipeline.

## 11. Recovery problems

- No clean version exists for files created *during* the attack (attacker
  payloads) → contained, honestly reported as "contained, not restored".
- Rename attacks: pre-rename version history is transferred to the new path
  before capture ordering, then renamed back post-restore — recovery is
  complete in content AND name (drill-verified).

## 12. Windows permission issues

- Termination can be denied for privileged processes; result is recorded as
  `TERMINATE_REFUSED` (never faked). **This repo was developed/tested on
  Linux; run `python verify_demo.py` once on the Windows demo machine** —
  psutil code paths and the simulator sandbox cross over, but examiner-laptop
  validation is part of demo prep.

## 13. Security weaknesses

- Vault PIN default `victim_user/1234` is a *demo credential* (env
  overrides: `ENTROPY_VAULT_USER/PIN`). Say so; do not present it as access
  control.
- Attacker control API requires bearer token (`ENTROPY_CONTROL_TOKEN`).
- Defender self-kill prevented by `DEFENDER_TOOLING_MARKERS` + self-PID
  checks; whitelisted system processes are never terminated.

## 14. Performance issues

- Entropy path is vectorised (numpy bincount, <1 ms per 64 KiB sample);
  events are batched (queue size/batch configurable). Sustained >10k-event
  storms are queue-bounded; beyond that, drops would be logged (not silent).
- Measured wall time for full containment+restore of a campaign event:
  ~1 ms defender-side (see forensic report `timeline`), attacker-kill wall
  clock 0.1–1.2 s live (watchdog latency dominates).

## 15. Single points of failure

- One pipeline process, one dashboard, one SQLite. `lab.py` exits if a child
  dies (documented; no auto-restart). Mitigation for the demo:
  `python main.py` health check + `python verify_demo.py` before walking in.

## 16. Attack scenarios the prototype cannot handle

- Encryption wholly inside another process's memory writing via an innocuous
  verified process (Living-off-the-Land); in-place encryption below entropy
  deltas *with* a legitimately verified process we refuse to kill
  (quarantine+restore still contains); attacks on files outside
  `ENTROPY_WATCH_FOLDERS`; kernel-mode ransomware. All stated openly.

## 17. PPT claims that are NOT implemented (say "proposed")

- 99.2% prevention, zero-day APT detection, kernel-level monitoring (Rust),
  IPFS, ELK/Prometheus/Grafana, PostgreSQL federation, Kubernetes, real
  blockchain consensus, "rollback" as a filesystem snapshot primitive
  (we implement **versioned clean-copy restore** instead — which is working
  and demonstrable). The 100% figure you may quote refers **only** to the
  lab benchmark battery: 8 attack families × seeds × 2 baseline modes,
  0 false quarantines — regenerable via `python -m benchmark`.
