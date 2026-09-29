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

export function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1048576).toFixed(2)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

/** Seconds -> "1m 04s" / "12s". */
export function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (!minutes) return `${rest}s`;
  return `${minutes}m ${String(rest).padStart(2, "0")}s`;
}

/** Local wall clock, HH:MM:SS. */
export function clockOf(date) {
  return date.toLocaleTimeString("en-GB", { hour12: false });
}

export function percent(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return 0;
  return Math.max(0, Math.min(100, number));
}
