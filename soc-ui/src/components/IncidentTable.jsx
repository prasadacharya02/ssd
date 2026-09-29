import Card, { CardLabel } from "./Card.jsx";
import { cx, formatFloat, timeOf } from "../lib/format.js";
import { InboxIcon } from "./icons.jsx";

const VERDICTS = {
  0: { label: "Ignored", cls: "border-slate-700/70 bg-slate-800/50 text-slate-400" },
  1: { label: "Alert", cls: "border-amber-500/20 bg-amber-500/10 text-amber-300" },
  2: { label: "Terminated", cls: "border-orange-500/20 bg-orange-500/10 text-orange-300" },
  3: { label: "Quarantined", cls: "border-red-500/20 bg-red-500/10 text-red-400" },
};

function fileName(path) {
  if (!path) return "—";
  const parts = String(path).split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function fileDir(path) {
  if (!path) return "";
  const parts = String(path).split(/[\\/]/);
  const dir = parts.slice(0, -1).join("/");
  return dir.length > 34 ? `…${dir.slice(-34)}` : dir;
}

function VerdictChip({ action }) {
  const verdict = VERDICTS[action] ?? VERDICTS[0];
  return (
    <span
      className={cx(
        "inline-flex rounded border px-2 py-0.5 text-[11px] font-medium",
        verdict.cls,
      )}
    >
      {verdict.label}
    </span>
  );
}

export default function IncidentTable({ events, query, onExport }) {
  const filtered = (events || []).filter((event) => {
    if (!query) return true;
    const haystack = [
      event.file_path,
      event.process_name,
      event.event_type,
      event.status,
      event.outcome,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  return (
    <Card className="lg:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardLabel>Incident feed</CardLabel>
          <p className="mt-1.5 text-[13px] text-slate-500">
            {filtered.length} event{filtered.length === 1 ? "" : "s"}
            {query ? ` matching “${query}”` : " · newest first"}
          </p>
        </div>
        <button
          type="button"
          onClick={onExport}
          className="rounded-md border border-slate-800 bg-canvas/60 px-3 py-1.5 text-xs font-medium text-slate-300 transition-all duration-200 hover:border-slate-600 hover:bg-slate-800/60 hover:text-slate-100"
        >
          Export JSON
        </button>
      </div>

      <div className="mt-5 overflow-hidden rounded-md border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-canvas/50 text-[11px] uppercase tracking-[0.12em] text-slate-500">
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">File</th>
                <th className="px-4 py-3 font-medium">Event</th>
                <th className="px-4 py-3 text-right font-medium">Entropy</th>
                <th className="px-4 py-3 font-medium">Process</th>
                <th className="px-4 py-3 font-medium">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-14 text-center">
                    <InboxIcon className="mx-auto h-5 w-5 text-slate-600" />
                    <p className="mt-3 text-[13px] text-slate-500">
                      {query
                        ? "No events match this search."
                        : "No incidents recorded yet. The feed updates live as the pipeline observes file activity."}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((event) => {
                  const delta = Number(event.entropy_delta) || 0;
                  return (
                    <tr
                      key={event.id}
                      className="border-b border-slate-800/70 transition-all duration-200 last:border-b-0 hover:bg-slate-800/30"
                    >
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs tabular-nums text-slate-400">
                        {timeOf(event.timestamp)}
                      </td>
                      <td className="max-w-[220px] px-4 py-3">
                        <p className="truncate font-medium text-slate-200">
                          {fileName(event.file_path)}
                        </p>
                        <p className="truncate text-[11px] text-slate-500">
                          {fileDir(event.file_path)}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {event.event_type ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                        <span className="text-slate-200">
                          {formatFloat(event.entropy)}
                        </span>
                        <span
                          className={cx(
                            "ml-2 text-[11px]",
                            Math.abs(delta) >= 0.5
                              ? "text-red-400"
                              : "text-slate-500",
                          )}
                        >
                          {delta >= 0 ? "+" : ""}
                          {formatFloat(delta)}
                        </span>
                      </td>
                      <td className="max-w-[160px] truncate px-4 py-3 font-mono text-xs text-slate-400">
                        {event.process_name ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <VerdictChip action={event.action} />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}
