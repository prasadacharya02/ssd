import { cx } from "../lib/format.js";

/** The card surface: panel background, hairline border, no shadows. */
export default function Card({ className, children, ...rest }) {
  return (
    <section
      className={cx("rounded-lg border border-slate-800 bg-panel p-5", className)}
      {...rest}
    >
      {children}
    </section>
  );
}

export function CardLabel({ children, className }) {
  return (
    <p
      className={cx(
        "text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function CardHeader({ label, hint, className, children }) {
  return (
    <div className={cx("flex items-start justify-between gap-3", className)}>
      <CardLabel>{label}</CardLabel>
      {children ?? (hint ? <span className="text-[11px] text-slate-500">{hint}</span> : null)}
    </div>
  );
}

const BUTTON_VARIANTS = {
  default:
    "border-slate-800 bg-canvas/60 text-slate-300 hover:border-slate-700 hover:text-slate-100",
  primary:
    "border-red-500/40 bg-red-500/10 text-red-200 hover:border-red-500/60 hover:bg-red-500/20",
  armed:
    "border-amber-500/50 bg-amber-500/15 text-amber-200 hover:bg-amber-500/25",
  subtle:
    "border-transparent bg-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200",
  success:
    "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20",
};

export function Button({
  variant = "default",
  className,
  icon: Icon,
  children,
  size = "md",
  ...rest
}) {
  return (
    <button
      type="button"
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-md border font-medium transition-all duration-200",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-800 disabled:hover:bg-canvas/60",
        size === "sm" ? "h-8 px-2.5 text-[12px]" : "h-9 px-3 text-[13px]",
        BUTTON_VARIANTS[variant] || BUTTON_VARIANTS.default,
        className,
      )}
      {...rest}
    >
      {Icon ? <Icon className="h-4 w-4 shrink-0" /> : null}
      {children}
    </button>
  );
}

export function Chip({ tone = "slate", className, children }) {
  const tones = {
    slate: "border-slate-800 bg-canvas/60 text-slate-400",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    red: "border-red-500/30 bg-red-500/10 text-red-300",
    sky: "border-sky-500/30 bg-sky-500/10 text-sky-300",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium",
        tones[tone] || tones.slate,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusDot({ tone = "slate", pulse = false, className }) {
  const tones = {
    slate: "bg-slate-600",
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
  };
  return (
    <span className={cx("relative flex h-1.5 w-1.5", className)}>
      {pulse ? (
        <span
          className={cx(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
            tones[tone],
          )}
        />
      ) : null}
      <span className={cx("relative inline-flex h-1.5 w-1.5 rounded-full", tones[tone])} />
    </span>
  );
}

export function StatTile({ label, value, unit, tone = "default", hint }) {
  const tones = {
    default: "text-slate-100",
    muted: "text-slate-400",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    red: "text-red-300",
  };
  return (
    <div className="rounded-md border border-slate-800 bg-canvas/40 px-3 py-2.5">
      <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>
      <p
        className={cx(
          "mt-1.5 font-mono text-[15px] font-semibold tabular-nums",
          tones[tone] || tones.default,
        )}
      >
        {value}
        {unit ? (
          <span className="ml-1 font-sans text-[11px] font-normal text-slate-500">
            {unit}
          </span>
        ) : null}
      </p>
      {hint ? <p className="mt-1 text-[11px] leading-tight text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function ProgressBar({ value, tone = "slate", className }) {
  const tones = {
    slate: "bg-slate-500",
    red: "bg-red-400",
    amber: "bg-amber-400",
    emerald: "bg-emerald-400",
  };
  return (
    <div className={cx("h-1 w-full overflow-hidden rounded-full bg-slate-800", className)}>
      <div
        className={cx("h-full rounded-full transition-all duration-300", tones[tone])}
        style={{ width: `${Math.max(0, Math.min(100, Number(value) || 0))}%` }}
      />
    </div>
  );
}
