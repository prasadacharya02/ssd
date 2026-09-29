import Card, { CardHeader, StatTile } from "./ui.jsx";
import { cx, formatBytes, formatInt } from "../lib/format.js";

export default function EstateSnapshot({ estate, familyExtension }) {
  const extensionTop = estate.extensions.slice(0, 5);
  const extensionMax = extensionTop.reduce(
    (max, item) => Math.max(max, item.files || 0),
    1,
  );

  return (
    <Card className="flex h-full flex-col">
      <CardHeader label="Victim estate" hint="victim_server/user_files" />

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <StatTile
          label="Files"
          value={estate.exists ? formatInt(estate.total) : "missing"}
          tone={estate.exists ? "default" : "red"}
        />
        <StatTile label="Size" value={formatBytes(estate.bytes)} tone="muted" />
        <StatTile
          label="Attackable"
          value={formatInt(estate.attackable)}
          tone="muted"
          hint="not yet locked"
        />
        <StatTile
          label={`Locked ${familyExtension || ""}`.trim()}
          value={formatInt(estate.locked)}
          tone={estate.locked ? "red" : "muted"}
        />
        <StatTile
          label="Ransom notes"
          value={formatInt(estate.notes)}
          tone={estate.notes ? "amber" : "muted"}
        />
        <StatTile
          label="Evidence held"
          value={formatInt(estate.evidence)}
          tone="muted"
          hint="quarantine vault"
        />
      </div>

      {extensionTop.length ? (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
            File mix
          </p>
          <ul className="mt-3 space-y-2">
            {extensionTop.map((item) => (
              <li key={item.ext} className="flex items-center gap-3">
                <span className="w-14 shrink-0 font-mono text-[11px] text-slate-400">
                  {item.ext}
                </span>
                <span className="h-1 flex-1 overflow-hidden rounded-full bg-slate-800">
                  <span
                    className={cx(
                      "block h-full rounded-full",
                      estate.locked ? "bg-red-400/80" : "bg-slate-600",
                    )}
                    style={{
                      width: `${Math.max(6, (item.files / extensionMax) * 100)}%`,
                    }}
                  />
                </span>
                <span className="w-8 shrink-0 text-right font-mono text-[11px] tabular-nums text-slate-500">
                  {item.files}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {estate.folders.length ? (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
            Folders
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {estate.folders.map((folder) => (
              <span
                key={folder.name}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-800 bg-canvas/60 px-2 py-1 text-[11px] text-slate-400"
              >
                {folder.name}
                <span className="font-mono tabular-nums text-slate-500">
                  {folder.files}
                </span>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-4 border-t border-slate-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        Counters read the live victim tree — the same directory the SOC pipeline
        watches. “Restore estate” rewrites the clean fixture baseline.
      </p>
    </Card>
  );
}
