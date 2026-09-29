/**
 * Runtime configuration for the operator console.
 *
 * Two sources, in priority order:
 *
 * 1. Values injected by the Python service into index.html. An operator sets
 *    these explicitly (ENTROPY_PUBLIC_*_URL) when the console must advertise
 *    a fixed address that the request cannot describe. They are left empty
 *    by default.
 * 2. The browser's own location. Resolving the sibling links here — rather
 *    than from the request Host the server saw — is what makes them correct
 *    behind every proxy: it uses the exact hostname the operator is already
 *    looking at, so a proxy that rewrites Host (many do) cannot break them.
 *
 * The port-labelled form used by hosted previews is handled explicitly:
 * "8001-host.example" -> "5000-host.example".
 */

const injected =
  (typeof window !== "undefined" && window.__ENTROPY_CONSOLE__) || {};

/** Placeholders still wrapped in underscores mean "not injected". */
function resolved(value) {
  if (!value || typeof value !== "string") return "";
  return value.startsWith("__") && value.endsWith("__") ? "" : value;
}

function currentLocation() {
  return typeof window !== "undefined" && window.location
    ? window.location
    : null;
}

/** This console's own port, from the URL or from a "8001-host" port label. */
function ownPort(location_) {
  if (location_.port) return location_.port;
  const label = /^(\d+)-/.exec(location_.hostname);
  return label ? label[1] : "";
}

/**
 * URL of a sibling service, derived from where this page is actually served.
 *
 * Handles the two shapes the lab is published in:
 *   "127.0.0.1:8001"       -> "127.0.0.1:5000"     (plain host:port)
 *   "8001-host.example"    -> "5000-host.example"  (port-labelled proxy)
 */
export function siblingUrl(port) {
  const location_ = currentLocation();
  if (!location_) return "";
  const { protocol, hostname } = location_;
  const own = ownPort(location_);

  if (own && hostname.startsWith(`${own}-`)) {
    return `${protocol}//${port}-${hostname.slice(own.length + 1)}`;
  }
  return `${protocol}//${hostname}:${port}`;
}

const SIBLING_PORTS = { victim: "5001", dashboard: "5000", attacker: "8001" };

export const controlToken = resolved(injected.token);

export const links = {
  victim: resolved(injected.victimUrl) || siblingUrl(SIBLING_PORTS.victim),
  dashboard:
    resolved(injected.dashboardUrl) || siblingUrl(SIBLING_PORTS.dashboard),
  attacker: resolved(injected.attackerUrl) || siblingUrl(SIBLING_PORTS.attacker),
};

/** Auth headers for the protected control routes. */
export function authHeaders(json = false) {
  const headers = json ? { "Content-Type": "application/json" } : {};
  if (controlToken) headers.Authorization = `Bearer ${controlToken}`;
  return headers;
}
