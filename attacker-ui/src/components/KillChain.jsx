import Card, { CardHeader } from "./ui.jsx";
import { cx, clockOf } from "../lib/format.js";
import { phaseLabel } from "../hooks/useAttackConsole.js";

const DOT_TONE = {
  slate: "bg-slate-500",
  sky: "bg-sky-400",
  amber: "bg-amber-400",
  red: "bg-red-400",
  emerald: "bg-emerald-400",
};
const TEXT_TONE = {
  slate: "text-slate-300",
  sky: "text-sky-300",
  amber: "text-amber-300",
  red: "text-red-300",
  emerald: "text-emerald-300",
};

function detailFor(entry, run) {
  if (entry.phase === "KILLED_BY_DEFENDER") {
    return `process terminated by defense · exit ${run.exitCode ?? 42}`;
  }
  if (entry.phase === "COMPLETED") {
    return `${entry.hit} of ${entry.targets} staged files overwritten`;
  }
  if (entry.phase === "STOPPED") return "operator SIGINT · clean exit";
  if (entry.phase === "PAUSED") return `at ${entry.hit}/${entry.targets} files`;
  if (entry.phase === "ENCRYPTING") return `${entry.targets} files staged`;
  if (entry.phase === "SCANNING") return "estate enumeration started";
  return "state change";
}

export default function KillChain({ timeline, run, onClear }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader label="Kill chain" hint="observed by this console">
        {timeline.length ? (
          <button
            type="button"
            onClick={onClear}
            className="text-[11px] text-slate-500 transition-colors duration-200 hover:text-slate-300"
          >
            Clear
          </button>
        ) : null}
      </CardHeader>

      {timeline.length === 0 ? (
        <p className="mt-4 text-[13px] leading-relaxed text-slate-500">
          No state transitions observed yet. Launch a payload and the console will
          record each phase change — including the moment the defender terminates
          the process.
        </p>
      ) : (
        <ol className="mt-4 space-y-0">
          {timeline.map((entry, index) => {
            const tone =
              entry.phase === "KILLED_BY_DEFENDER"
                ? "emerald"
                : entry.phase === "ENCRYPTING"
                  ? "red"
                  : entry.phase === "SCANNING"
                    ? "sky"
                    : entry.phase === "PAUSED"
                      ? "amber"
                      : "slate";
            return (
              <li key={entry.id} className="relative flex gap-3 pb-4 last:pb-0">
                {index !== timeline.length - 1 ? (
                  <span className="absolute left-[3px] top-3 h-full w-px bg-slate-800" />
                ) : null}
                <span
                  className={cx(
                    "relative mt-1.5 h-[7px] w-[7px] shrink-0 rounded-full",
                    DOT_TONE[tone],
                  )}
                />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <p
                      className={cx(
                        "text-[13px] font-medium",
                        TEXT_TONE[tone],
                      )}
                    >
                      {phaseLabel(entry.phase)}
                    </p>
                    <span className="font-mono text-[11px] tabular-nums text-slate-500">
                      {clockOf(entry.at)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {detailFor(entry, run)}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
