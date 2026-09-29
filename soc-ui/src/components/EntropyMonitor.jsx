import Card, { CardLabel } from "./Card.jsx";
import { cx, formatFloat, timeOf } from "../lib/format.js";

/**
 * Live Entropy Monitor.
 *
 * Every plotted value is a real detector output: the exact Shannon
 * entropy reading the decision engine scored for that file event,
 * streamed over socket.io as the event was recorded (plus a polled
 * backfill of recent history from /api/entropy). Nothing is simulated
 * or hard-coded:
 *
 *   - warning / critical / baseline guide lines come from
 *     /api/entropy/config, which reads the decision-engine config;
 *   - the detection marker sits on the first event the engine
 *     flagged (action >= 1) inside the visible window;
 *   - quarantine and restore markers correlate with the event
 *     timeline in the incident table below.
 *
 * Data flow: Matrix (file stream) -> decision engine -> events table /
 * socket `new_event` -> this chart. Same value end to end.
 */

const W = 760;           // viewBox width (stretches responsively)
const H = 220;           // viewBox height
const PAD = { top: 14, right: 14, bottom: 26, left: 34 };
const MAX_BITS = 8.0;    // Shannon ceiling for 8-bit bytes

const plotW = W - PAD.left - PAD.right;
const plotH = H - PAD.top - PAD.bottom;

const yOf = (v) => PAD.top + plotH - (Math.max(0, Math.min(MAX_BITS, v)) / MAX_BITS) * plotH;
const xOf = (i, n) => PAD.left + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW);

function linePath(points, key) {
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"}${xOf(i, points.length).toFixed(1)},${yOf(Number(p[key]) || 0).toFixed(1)}`)
    .join(" ");
}

function shortName(filePath) {
  if (!filePath) return "—";
  const parts = String(filePath).split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? String(filePath);
}

function statusOf(latest, warning) {
  const outcome = String(latest?.outcome ?? "");
  const action = Number(latest?.action ?? 0);
  if (outcome.includes("+RESTORED"))
    return { label: "RECOVERED", cls: "text-emerald-400" };
  if (outcome.includes("QUARANTINE") || action >= 2)
    return { label: "CONTAINED", cls: "text-red-400" };
  if (action >= 1) return { label: "SUSPICIOUS", cls: "text-red-400" };
  if (Number(latest?.entropy ?? 0) >= warning * 0.9)
    return { label: "ELEVATED", cls: "text-amber-400" };
  return { label: "NORMAL", cls: "text-emerald-400" };
}

/** One detection marker: vertical guide + labelled flag at the top. */
function Marker({ x, color, label }) {
  return (
    <g>
      <line x1={x} y1={PAD.top} x2={x} y2={PAD.top + plotH} stroke={color} strokeWidth="1" strokeDasharray="2 3" opacity="0.85" />
      <text x={x + 3} y={PAD.top + 8} fill={color} fontSize="8.5" fontWeight="700" letterSpacing="0.06em">
        {label}
      </text>
    </g>
  );
}

function GuideLine({ y, color, label, dash = "4 4" }) {
  return (
    <g>
      <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y} stroke={color} strokeWidth="1" strokeDasharray={dash} opacity="0.7" />
      <text x={W - PAD.right} y={y - 3} textAnchor="end" fill={color} fontSize="8" fontWeight="600" letterSpacing="0.05em">
        {label}
      </text>
    </g>
  );
}

export default function EntropyMonitor({ points = [], config, connected }) {
  const visible = Array.isArray(points) ? points.filter((p) => Number.isFinite(Number(p?.entropy))) : [];
  const latest = visible.length ? visible[visible.length - 1] : null;

  // Thresholds — from the backend config endpoint, never hard-coded.
  const warning = Number(config?.warning_threshold);
  const critical = Number(config?.critical_threshold);
  const baseline = Number.isFinite(Number(config?.baseline)) ? Number(config.baseline) : null;
  const maxBits = Number.isFinite(Number(config?.max_bits)) ? Number(config.max_bits) : MAX_BITS;

  const status = statusOf(latest, Number.isFinite(warning) ? warning : Infinity);

  // Detection-moment markers within the visible window.
  const firstDetected = visible.find((p) => Number(p.action) >= 1);
  const firstQuarantined = visible.find((p) => String(p.outcome ?? "").includes("QUARANTINE"));
  const firstRestored = visible.find((p) => String(p.outcome ?? "").includes("+RESTORED"));
  const idx = (p) => (p ? visible.indexOf(p) : -1);

  return (
    <Card className="md:col-span-2 lg:col-span-12">
      {/* Header: label, live indicator, readouts */}
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <CardLabel>Live entropy monitor</CardLabel>
          <span className={cx("inline-block h-1.5 w-1.5 rounded-full", connected ? "bg-emerald-400" : "bg-red-400")} />
          <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
            {connected ? "streaming" : "reconnecting"}
          </span>
        </div>
        <dl className="flex flex-wrap items-baseline gap-x-5 gap-y-1 text-[11px] tabular-nums text-slate-500">
          <span>
            Current{" "}
            <span className={cx("text-sm font-semibold", status.cls)}>
              {latest ? formatFloat(latest.entropy) : "—"}
            </span>
            <span className="text-slate-600"> bits/byte</span>
          </span>
          <span>Baseline <span className="font-semibold text-slate-300">{baseline !== null ? formatFloat(baseline) : "—"}</span></span>
          <span>Warning <span className="font-semibold text-amber-400">{Number.isFinite(warning) ? formatFloat(warning, 1) : "—"}</span></span>
          <span>Critical <span className="font-semibold text-red-400">{Number.isFinite(critical) ? formatFloat(critical, 1) : "—"}</span></span>
          <span>
            Status <span className={cx("font-semibold", status.cls)}>{latest ? status.label : "—"}</span>
          </span>
        </dl>
      </div>

      {visible.length === 0 ? (
        <p className="mt-6 text-[13px] text-slate-500">
          Monitoring active — waiting for file events. Real entropy readings
          appear here the moment the pipeline observes activity, and during a
          demo you will see the line rise, cross warning/critical, and drop
          back to baseline once the process is contained and files restore.
        </p>
      ) : (
        <div className="mt-4">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-56 w-full"
            role="img"
            aria-label="Live entropy graph: time on the X axis, Shannon entropy in bits per byte on the Y axis"
          >
            {/* Y gridlines + labels (0 .. max_bits step 2) */}
            {Array.from({ length: maxBits / 2 + 1 }, (_, k) => k * 2).map((tick) => (
              <g key={tick}>
                <line x1={PAD.left} y1={yOf(tick)} x2={W - PAD.right} y2={yOf(tick)} stroke="#1e293b" strokeWidth="1" />
                <text x={PAD.left - 6} y={yOf(tick) + 3} textAnchor="end" fill="#64748b" fontSize="9" className="tabular-nums">
                  {tick}
                </text>
              </g>
            ))}
            <text x={PAD.left - 26} y={PAD.top - 4} fill="#64748b" fontSize="8" letterSpacing="0.05em">
              bits/byte
            </text>

            {/* X axis timestamps (~5 labels, real event times) */}
            {visible.map((p, i) => {
              const step = Math.max(1, Math.ceil(visible.length / 5));
              return i % step === 0 || i === visible.length - 1 ? (
                <text key={p.id ?? i} x={xOf(i, visible.length)} y={H - 8} textAnchor="middle" fill="#64748b" fontSize="8.5" className="tabular-nums">
                  {timeOf(p.timestamp)}
                </text>
              ) : null;
            })}

            {/* Threshold + baseline guides from the backend config */}
            {baseline !== null && <GuideLine y={yOf(baseline)} color="#475569" label={`BASELINE ${formatFloat(baseline, 1)}`} dash="1 3" />}
            {Number.isFinite(warning) && <GuideLine y={yOf(warning)} color="#f59e0b" label={`WARNING ${formatFloat(warning, 1)}`} />}
            {Number.isFinite(critical) && <GuideLine y={yOf(critical)} color="#ef4444" label={`CRITICAL ${formatFloat(critical, 1)}`} />}

            {/* ΔEntropy — faint secondary trace (measured, not derived on the fly) */}
            <path d={linePath(visible, "entropy_delta")} fill="none" stroke="#64748b" strokeWidth="1" strokeDasharray="2 3" opacity="0.55" />

            {/* Entropy area + line */}
            <path
              d={`${linePath(visible, "entropy")} L${xOf(visible.length - 1, visible.length)},${(PAD.top + plotH).toFixed(1)} L${xOf(0, visible.length)},${(PAD.top + plotH).toFixed(1)} Z`}
              fill="#10b981"
              opacity="0.07"
            />
            <path d={linePath(visible, "entropy")} fill="none" stroke="#10b981" strokeWidth="1.6" strokeLinejoin="round" />

            {/* Flagged points + detection / response markers */}
            {visible.map((p, i) =>
              Number(p.action) >= 1 ? (
                <circle
                  key={`hot-${p.id ?? i}`}
                  cx={xOf(i, visible.length)}
                  cy={yOf(Number(p.entropy) || 0)}
                  r="3"
                  fill="#ef4444"
                  stroke="#0f172a"
                  strokeWidth="1"
                >
                  <title>{`${timeOf(p.timestamp)} · ${shortName(p.file_path)} · H=${formatFloat(p.entropy)} · flagged`}</title>
                </circle>
              ) : null,
            )}
            {firstDetected && <Marker x={xOf(idx(firstDetected), visible.length)} color="#ef4444" label="DETECTED" />}
            {firstQuarantined && idx(firstQuarantined) !== idx(firstDetected) && (
              <Marker x={xOf(idx(firstQuarantined), visible.length)} color="#f97316" label="QUARANTINED" />
            )}
            {firstRestored && <Marker x={xOf(idx(firstRestored), visible.length)} color="#10b981" label="RESTORED" />}

            {/* Latest point pulse */}
            {latest && (
              <circle
                cx={xOf(visible.length - 1, visible.length)}
                cy={yOf(Number(latest.entropy) || 0)}
                r="3.5"
                fill="#10b981"
                stroke="#0f172a"
                strokeWidth="1.5"
              />
            )}
          </svg>

          {/* Footer: legend + correlation hint */}
          <div className="mt-1 flex flex-wrap items-center gap-x-5 gap-y-1 text-[10px] text-slate-500">
            <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-4 bg-emerald-400" /> Entropy</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-0 w-4 border-t border-dashed border-slate-500" /> ΔEntropy</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-0 w-4 border-t border-dashed border-amber-400" /> Warning</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-0 w-4 border-t border-dashed border-red-400" /> Critical</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-0 w-4 border-t border-dotted border-slate-600" /> Baseline</span>
            {latest && (
              <span className="ml-auto text-slate-600">
                Latest: {shortName(latest.file_path)}
                {latest.process_name ? ` · ${latest.process_name}` : ""} · {timeOf(latest.timestamp)}
              </span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
