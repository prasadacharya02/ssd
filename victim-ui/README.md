# Victim File Explorer (port 5001)

Windows 11–style React + Tailwind UI served by the existing Flask victim server.
No CDN, external fonts, or browser-facing localhost dependencies are required.

## Build and test

```sh
cd victim-ui
npm ci
npm test
npm run build
```

The checked-in build is emitted to `victim_server/static/explorer/`. Flask serves
its index at `/`; the previous Jinja page remains a fallback when no build exists.
Rebuild after changing React source. The Python API and vault security are unchanged.

For development, run Flask on port 5001 and `npm run dev` in this directory.
Vite listens on 0.0.0.0:5174 and proxies same-origin `/api` requests to Flask.

## Simulation versus live data

- **Simulation layout** (initial selection): displays the specified folder counts
  and sizes, explicitly labeled as sample counts in the bottom explorer strip.
- **Live filesystem**: uses `/api/folders` counts and sizes, refreshed every three
  seconds. Navigating a folder always reads actual files from `/api/files/<folder>`.
- The pulsing **Ransomware Shield - Monitoring** pill is the requested simulation
  overlay, not a claim that the defender is connected. Its tooltip explains this;
  the victim API does not expose an agent heartbeat.
- Vault login, logout, session expiry, and previews use the existing backend.
  Quarantine contents never load before authentication.
- New/Cut/Copy/Paste/Rename are deliberately disabled: this is a read-only explorer.
- Minimize and Close hide the simulated window, not the browser; the VM ribbon
  opens it again. Maximize fills the available viewport.

Native `<dialog>` provides modal focus containment and Escape dismissal. Search
survives background polling. Write actions remain disabled. Normal folders expose
only file names, sizes and timestamps, with no attack assessments.
