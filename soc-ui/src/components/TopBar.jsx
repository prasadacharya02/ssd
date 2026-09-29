import { cx } from "../lib/format.js";
import { BellIcon, MenuIcon, SearchIcon } from "./icons.jsx";

function OmniSearch({ query, onQueryChange }) {
  return (
    <label className="relative block w-full max-w-md">
      <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <input
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="Search incidents, files, processes…"
        spellCheck={false}
        className={cx(
          "h-9 w-full rounded-md border border-slate-800 bg-panel pl-9 pr-14 text-sm text-slate-200",
          "placeholder:text-slate-500 transition-all duration-200",
          "focus:border-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-700/50",
        )}
      />
      <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 sm:block">
        ⌘K
      </kbd>
    </label>
  );
}

function ConnectionChip({ connected }) {
  return (
    <span
      className={cx(
        "hidden items-center gap-2 rounded-md border border-slate-800 bg-panel px-3 py-1.5 text-xs font-medium md:inline-flex",
        connected ? "text-slate-300" : "text-slate-500",
      )}
    >
      <span
        className={cx(
          "h-1.5 w-1.5 rounded-full",
          connected ? "bg-emerald-400" : "bg-slate-600",
        )}
      />
      {connected ? "Live" : "Reconnecting"}
    </span>
  );
}

function UserStatus() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-200">
        GK
      </div>
      <div className="hidden leading-tight sm:block">
        <p className="text-[13px] font-medium text-slate-200">Guru Krishna</p>
        <p className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <span className="h-1 w-1 rounded-full bg-emerald-400" />
          Analyst · on shift
        </p>
      </div>
    </div>
  );
}

export default function TopBar({
  query,
  onQueryChange,
  connected,
  alertCount,
  onOpenMobile,
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-canvas/95 backdrop-blur-sm">
      <div className="flex h-16 items-center gap-4 px-4 sm:px-6">
        <button
          type="button"
          onClick={onOpenMobile}
          className="rounded-md border border-slate-800 bg-panel p-2 text-slate-400 transition-all duration-200 hover:bg-slate-800/60 hover:text-slate-200 lg:hidden"
          aria-label="Open navigation"
        >
          <MenuIcon className="h-4 w-4" />
        </button>

        <OmniSearch query={query} onQueryChange={onQueryChange} />

        <div className="ml-auto flex items-center gap-3 sm:gap-4">
          <ConnectionChip connected={connected} />

          <button
            type="button"
            className="relative rounded-md border border-slate-800 bg-panel p-2 text-slate-400 transition-all duration-200 hover:bg-slate-800/60 hover:text-slate-200"
            aria-label={`Notifications (${alertCount} active alerts)`}
          >
            <BellIcon className="h-4 w-4" />
            {alertCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500/90 px-1 text-[10px] font-semibold text-white">
                {alertCount > 99 ? "99" : alertCount}
              </span>
            )}
          </button>

          <div className="hidden h-6 w-px bg-slate-800 sm:block" />
          <UserStatus />
        </div>
      </div>
    </header>
  );
}
