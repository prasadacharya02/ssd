import Card, { CardLabel } from "./Card.jsx";
import { cx, formatFloat, formatInt } from "../lib/format.js";

const THREAT_TONE = {
  MINIMAL: { text: "text-emerald-400", bar: "bg-emerald-400" },
  ELEVATED: { text: "text-amber-400", bar: "bg-amber-400" },
  HIGH: { text: "text-orange-400", bar: "bg-orange-400" },
  CRITICAL: { text: "text-red-400", bar: "bg-red-400" },
};

/**
 * Dominant module — threat posture over the last five minutes.
 * Occupies the full left column on desktop to anchor the hierarchy.
 */
function ThreatLevelCard({ threat }) {
  const label = threat?.label ?? "—";
  const tone = THREAT_TONE[label] ?? { text: "text-slate-300", bar: "bg-slate-500" };
  const level = threat?.level ?? 0;
  const filled = Math.min(5, Math.ceil(level / 20) || (level > 0 ? 1 : 0));

  return (
    <Card className="flex flex-col justify-between gap-8 md:col-span-2 lg:col-span-5 lg:row-span-2">
      <div>
        <div className="flex items-baseline justify-between">
          <CardLabel>Threat level</CardLabel>
          <span className="text-[11px] text-slate-500">Last 5 minutes</span>
        </div>
        <p
          className={cx(
            "mt-4 text-[42px] font-semibold leading-none tracking-tight tabular-nums",
            tone.text,
          )}
        >
          {label}
        </p>
        <p className="mt-3 max-w-xs text-[13px] leading-relaxed text-slate-500">
          Weighted by terminated events and alert volume inside the pipeline’s
          rolling window.
        </p>
      </div>

      <div>
        <div className="flex items-end justify-between">
          <div>
            <p className="text-[11px] text-slate-500">Score</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-slate-100">
              {formatInt(level)}
              <span className="text-sm font-normal text-slate-500"> / 100</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-slate-500">Window activity</p>
            <p className="mt-1 text-[13px] text-slate-300 tabular-nums">
              {formatInt(threat?.recent_threats)} alerts ·{" "}
              {formatInt(threat?.recent_critical)} critical
            </p>
          </div>
        </div>
        <div className="mt-4 flex gap-1.5">
          {[1, 2, 3, 4, 5].map((step) => (
            <span
              key={step}
              className={cx(
                "h-1 flex-1 rounded-full transition-all duration-200",
                step <= filled ? tone.bar : "bg-slate-800",
              )}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}

function EventsCard({ stats }) {
  return (
    <Card className="lg:col-span-4">
      <CardLabel>Events monitored</CardLabel>
      <p className="mt-4 text-3xl font-semibold tabular-nums tracking-tight text-slate-100">
        {formatInt(stats?.total)}
      </p>
      <p className="mt-2 text-[13px] text-slate-500">
        {formatInt(stats?.threats)} flagged as threats since reset
      </p>
    </Card>
  );
}

function ResponseCard({ stats }) {
  return (
    <Card className="lg:col-span-3">
      <CardLabel>Automated response</CardLabel>
      <dl className="mt-4 space-y-3">
        <div className="flex items-center justify-between">
          <dt className="text-[13px] text-slate-400">Terminated</dt>
          <dd className="text-sm font-semibold tabular-nums text-slate-100">
            {formatInt(stats?.terminated)}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-[13px] text-slate-400">Quarantined</dt>
          <dd className="text-sm font-semibold tabular-nums text-red-400">
            {formatInt(stats?.quarantined)}
          </dd>
        </div>
        <div className="flex items-center justify-between border-t border-slate-800 pt-3">
          <dt className="text-[13px] text-slate-400">Restored</dt>
          <dd className="text-sm font-semibold tabular-nums text-emerald-400">
            {formatInt(stats?.recovery)}
          </dd>
        </div>
      </dl>
    </Card>
  );
}

/**
 * Entropy telemetry strip — last 24 readings, oldest → newest.
 * Bars above the ransomware threshold are flagged, not decorated.
 */
function EntropyCard({ entropy }) {
  const points = Array.isArray(entropy)
    ? entropy.slice(0, 24).reverse()
    : [];
  const latest = points.length ? points[points.length - 1] : null;
  const THRESHOLD = 7.0;

  return (
    <Card className="md:col-span-2 lg:col-span-7">
      <div className="flex items-baseline justify-between">
        <CardLabel>Entropy telemetry</CardLabel>
        {latest && (
          <span className="text-[11px] tabular-nums text-slate-500">
            Latest {formatFloat(latest.entropy)} · Δ {formatFloat(latest.entropy_delta)}
          </span>
        )}
      </div>

      {points.length === 0 ? (
        <p className="mt-6 text-[13px] text-slate-500">
          No entropy readings yet. Readings appear as soon as the pipeline
          observes file activity.
        </p>
      ) : (
        <div className="mt-6 flex h-12 items-end gap-[3px]">
          {points.map((point, index) => {
            const value = Number(point.entropy) || 0;
            const height = Math.max(4, Math.min(48, (value / 8) * 48));
            const hot = value >= THRESHOLD;
            return (
              <span
                key={index}
                title={`${point.file_path ?? ""} · ${formatFloat(value)}`}
                className={cx(
                  "flex-1 rounded-[1px] transition-all duration-200",
                  hot ? "bg-red-400/90" : "bg-slate-600",
                )}
                style={{ height: `${height}px` }}
              />
            );
          })}
        </div>
      )}
    </Card>
  );
}

/**
 * Asymmetric metric band: one dominant threat module on the left,
 * three uneven supporting modules on the right. No 4-up square grid.
 */
export default function MetricBoard({ stats, threat, entropy }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-12 lg:auto-rows-fr">
      <ThreatLevelCard threat={threat} />
      <EventsCard stats={stats} />
      <ResponseCard stats={stats} />
      <EntropyCard entropy={entropy} />
    </div>
  );
}
