/** Thin same-origin client for the attacker service REST API. */

import { authHeaders } from "./console-config.js";

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      (payload && payload.error) || `${url} -> HTTP ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
}

export function getJSON(url) {
  return request(url);
}

function post(url, body) {
  return request(url, {
    method: "POST",
    headers: authHeaders(Boolean(body)),
    body: body ? JSON.stringify(body) : undefined,
  });
}

export const api = {
  families: () => getJSON("/api/families"),
  stats: () => getJSON("/api/stats"),
  targets: () => getJSON("/api/targets"),
  launch: (family) => post("/api/launch", { family }),
  stop: () => post("/api/stop"),
  pause: () => post("/api/pause"),
  resume: () => post("/api/resume"),
  speed: (factor) => post("/api/speed", { factor }),
  reset: () => post("/api/reset"),
};
