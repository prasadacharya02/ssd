/**
 * Runtime configuration injected by the Python service into index.html.
 *
 * In `npm run dev` mode the placeholders are unresolved, so everything falls
 * back to the Vite dev server's proxy (`/api` -> 127.0.0.1:8001) and to
 * same-origin sibling ports.
 */

const injected =
  (typeof window !== "undefined" && window.__ENTROPY_CONSOLE__) || {};

/** Placeholders still wrapped in underscores mean "not injected". */
function resolved(value) {
  if (!value || typeof value !== "string") return "";
  return value.startsWith("__") && value.endsWith("__") ? "" : value;
}

const host =
  typeof window !== "undefined" && window.location ? window.location.hostname : "";

export const controlToken = resolved(injected.token);

export const links = {
  victim: resolved(injected.victimUrl) || `http://${host}:5001`,
  dashboard: resolved(injected.dashboardUrl) || `http://${host}:5000`,
  attacker: resolved(injected.attackerUrl) || `http://${host}:8001`,
};

/** Auth headers for the protected control routes. */
export function authHeaders(json = false) {
  const headers = json ? { "Content-Type": "application/json" } : {};
  if (controlToken) headers.Authorization = `Bearer ${controlToken}`;
  return headers;
}
