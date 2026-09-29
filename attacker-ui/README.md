# Entropy Attacker Operator Console (port 8001)

React + Tailwind operator console for the controlled attack half of the lab.
It is served by the dependency-free stdlib HTTP service in
`attacker_server/app.py`; no Node runtime is needed at demo time.

## Develop

```bash
npm install
npm run dev          # Vite dev server on :8001 proxy target, UI on :5175
```

Run the Python service alongside so the proxy has data:

```bash
python attacker_server/app.py
```

## Build

```bash
npm run build        # emits ../attacker_server/static/console/
npm test             # jsdom render tests (vitest + @testing-library/react)
```

The checked-in build is committed so a fresh clone serves the redesigned
console immediately. If the bundle is missing, `app.py` falls back to the
legacy single-file console in `attacker_server/templates/attacker.html`.

## Data

All panels read the service REST API on the same origin:

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/families` | GET | Shared ransomware-family catalog (`catalog.py`) |
| `/api/stats` | GET | Live process phase, counters, rate, streamed log |
| `/api/targets` | GET | Read-only victim estate summary (counts, sizes, mix) |
| `/api/log` | GET | Timestamped campaign log export |
| `/api/launch` | POST | Launch a family as a separate OS process |
| `/api/stop` | POST | Operator stop (SIGINT, clean exit) |
| `/api/pause` `/api/resume` | POST | Control-file pause/resume of the running process |
| `/api/speed` | POST | Rate multiplier 0.1×–5× |
| `/api/reset` | POST | Rewrite the clean fixture baseline |

Control routes require either loopback access (no token configured) or
`Authorization: Bearer <ENTROPY_CONTROL_TOKEN>`. `app.py` injects the token,
sibling-service links and the console configuration into `index.html` at
request time — the same contract the legacy template used.

## What the console shows

- **Payload catalog** — the ten simulated families with search and keyboard
  selection (`1`–`9`, `0`).
- **Campaign control** — two-step launch confirmation, pause/resume, operator
  abort, estate restore, log export, and a 0.1×–5× rate slider.
- **Telemetry** — phase, staged/encrypted/skipped/note counters, bytes
  overwritten, observed rate, elapsed time, exit code.
- **Kill chain** — phase transitions observed by the console while polling,
  including the defender termination verdict (exit 42).
- **Victim estate** — file/byte totals, attackable count, locked artifacts,
  ransom notes, quarantine evidence held by the SOC.
- **Process console** — streamed process output with levels, filters, grep,
  follow mode, copy, and `campaign.log` export.

Nothing on this page is inferred: every number comes from `/api/stats` or
`/api/targets`, and the kill-chain timeline is explicitly labelled as observed
by the console.

## Safety

- The engine is confined to `victim_server/user_files` by `safe_path()`.
- Files are overwritten with `os.urandom()`; no real user data is touched.
- This is a lab fixture estate — the console says so on every screen.
