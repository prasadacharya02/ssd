import { useMemo, useState } from "react";
import Card, { CardHeader } from "./ui.jsx";
import { SearchIcon } from "./icons.jsx";
import { cx } from "../lib/format.js";

function FamilyRow({ family, index, selected, disabled, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(family.id)}
      disabled={disabled}
      className={cx(
        "group relative w-full rounded-md border px-3 py-2.5 text-left transition-all duration-200",
        "disabled:cursor-not-allowed",
        selected
          ? "border-slate-700 bg-slate-800/60"
          : "border-transparent hover:border-slate-800 hover:bg-slate-800/30",
        disabled && !selected ? "opacity-50" : null,
      )}
    >
      {selected ? (
        <span className="absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-full bg-amber-400" />
      ) : null}

      <div className="flex items-center gap-2">
        <span
          className={cx(
            "font-mono text-[11px]",
            selected ? "text-amber-300" : "text-slate-600",
          )}
        >
          {String(index + 1).padStart(2, "0")}
        </span>
        <span
          className={cx(
            "truncate text-[13px] font-medium",
            selected ? "text-slate-100" : "text-slate-300",
          )}
        >
          {family.short_name || family.name}
        </span>
        <span className="ml-auto shrink-0 font-mono text-[11px] text-slate-500">
          {family.extension}
        </span>
      </div>

      <p className="mt-1 truncate pl-6 text-[11px] text-slate-500">
        {family.style || "Simulated family"} · {family.speed || "—"}
      </p>
    </button>
  );
}

export default function PayloadCatalog({
  families,
  selected,
  onSelect,
  locked,
  hint,
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return families;
    return families.filter((family) =>
      [family.name, family.short_name, family.id, family.extension, family.style]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [families, query]);

  return (
    <Card className="flex h-full flex-col p-4">
      <CardHeader label="Payload catalog" hint={`${families.length} families`} />

      <label className="relative mt-3 block">
        <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter payloads"
          spellCheck={false}
          className="h-9 w-full rounded-md border border-slate-800 bg-canvas/60 pl-8 pr-3 text-[13px] text-slate-200 placeholder:text-slate-500 focus:border-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-700/50"
        />
      </label>

      <div className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto pr-0.5">
        {filtered.length === 0 ? (
          <p className="px-1 py-6 text-center text-[12px] text-slate-500">
            No payload matches “{query}”.
          </p>
        ) : (
          filtered.map((family, index) => {
            // Keep the catalog's own numbering — those digits are shortcuts.
            const catalogIndex = families.indexOf(family);
            return (
              <FamilyRow
                key={family.id}
                family={family}
                index={catalogIndex >= 0 ? catalogIndex : index}
                selected={family.id === selected}
                disabled={locked}
                onSelect={onSelect}
              />
            );
          })
        )}
      </div>

      <p className="mt-3 border-t border-slate-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        {hint ||
          "Every family overwrites fixture files in victim_server/user_files only — the engine is confined to that tree."}
      </p>
    </Card>
  );
}
