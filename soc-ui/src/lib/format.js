/** Small shared helpers — formatting only, no presentation. */

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

const intFormat = new Intl.NumberFormat("en-US");

export function formatInt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return intFormat.format(Number(value));
}

export function formatFloat(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toFixed(digits);
}

/** "2026-09-29 14:02:11" or ISO string -> "14:02:11". */
export function timeOf(timestamp) {
  if (!timestamp) return "—";
  const normalized = String(timestamp).replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return String(timestamp).slice(11, 19);
  return date.toLocaleTimeString("en-GB", { hour12: false });
}

/** Short relative label, e.g. "12s ago", "4m ago". */
export function relativeFrom(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function shortHash(value, head = 10, tail = 6) {
  if (!value) return "—";
  const text = String(value);
  if (text.length <= head + tail + 1) return text;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}
