# Entropy SOC UI

React + Tailwind front end for the SOC dashboard served by the Flask app on
port 5000. Design language: refined dark mode (`#0B0F19` canvas, `#131B2E`
panels, `border-slate-800` hairlines), Inter typography, no gradients or glow.

## Develop

```bash
npm install
npm run dev          # Vite dev server on :5173, proxies /api → :5000
```

Run the Flask backend (`python app.py`) alongside so the proxy has data.

## Build

```bash
npm run build        # emits ../dashboard/static/soc/
```

Flask serves the bundle at `/` (falls back to the legacy template if the
bundle is missing). The legacy dashboard remains at `/legacy`.

## Data

All panels read live REST endpoints (`/api/stats`, `/api/threat-level`,
`/api/events`, `/api/dqn/last`, `/api/blockchain/status`, `/api/entropy`,
`/api/pipeline`) and subscribe to the Socket.IO stream (`new_event`,
`live_update`). Polling is the resilience fallback.
