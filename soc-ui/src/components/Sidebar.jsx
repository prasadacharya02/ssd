import { cx, relativeFrom } from "../lib/format.js";
import {
  CloseIcon,
  CrosshairIcon,
  ServerIcon,
  ShieldIcon,
  SlidersIcon,
} from "./icons.jsx";

export const NAV = [
  {
    section: "Operations",
    items: [
      { id: "incidents", label: "Incidents", icon: ShieldIcon },
      { id: "hunting", label: "Threat Hunting", icon: CrosshairIcon },
    ],
  },
  {
    section: "Infrastructure",
    items: [
      { id: "assets", label: "Assets", icon: ServerIcon },
      { id: "settings", label: "Settings", icon: SlidersIcon },
    ],
  },
];

function BrandMark() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-panel">
      <span className="font-mono text-[13px] font-semibold tracking-tight text-slate-100">
        En
      </span>
    </div>
  );
}

function NavLinks({ view, onSelect }) {
  return (
    <nav className="space-y-6">
      {NAV.map((group) => (
        <div key={group.section}>
          <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500">
            {group.section}
          </p>
          <ul className="space-y-1">
            {group.items.map((item) => {
              const active = view === item.id;
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id)}
                    className={cx(
                      "group relative flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-all duration-200",
                      active
                        ? "bg-slate-800/70 text-slate-100"
                        : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200",
                    )}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-slate-200" />
                    )}
                    <Icon
                      className={cx(
                        "h-4 w-4 shrink-0 transition-colors duration-200",
                        active
                          ? "text-slate-100"
                          : "text-slate-500 group-hover:text-slate-300",
                      )}
                    />
                    <span className="font-medium">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function PipelineStatus({ pipeline }) {
  const online = Boolean(pipeline?.online);
  return (
    <div className="rounded-md border border-slate-800 bg-canvas/60 p-4">
      <div className="flex items-center gap-2">
        <span
          className={cx(
            "h-1.5 w-1.5 rounded-full",
            online ? "bg-emerald-400" : "bg-slate-600",
          )}
        />
        <p className="text-xs font-medium text-slate-300">
          {online ? "Detection pipeline online" : "Pipeline offline"}
        </p>
      </div>
      <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
        {online
          ? `Heartbeat ${relativeFrom(pipeline?.age_seconds)} · watching ${
              pipeline?.watch_folders?.length || 0
            } folder${pipeline?.watch_folders?.length === 1 ? "" : "s"}`
          : "No recent heartbeat from the watcher process."}
      </p>
    </div>
  );
}

function SidebarBody({ view, onSelect, pipeline }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
        <BrandMark />
        <div>
          <p className="text-[15px] font-semibold tracking-tight text-slate-100">
            Entropy
          </p>
          <p className="text-[11px] text-slate-500">Security Operations</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-6">
        <NavLinks view={view} onSelect={onSelect} />
      </div>

      <div className="px-3 pb-6">
        <PipelineStatus pipeline={pipeline} />
      </div>
    </div>
  );
}

export default function Sidebar({
  view,
  onSelect,
  pipeline,
  mobileOpen,
  onCloseMobile,
}) {
  return (
    <>
      {/* Desktop: persistent rail */}
      <aside className="sticky top-0 hidden h-screen w-[236px] shrink-0 border-r border-slate-800 bg-panel lg:block">
        <SidebarBody view={view} onSelect={onSelect} pipeline={pipeline} />
      </aside>

      {/* Mobile: overlay drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="absolute inset-y-0 left-0 w-[260px] border-r border-slate-800 bg-panel">
            <button
              type="button"
              onClick={onCloseMobile}
              className="absolute right-3 top-4 rounded-md p-2 text-slate-500 transition-all duration-200 hover:bg-slate-800/60 hover:text-slate-200"
              aria-label="Close navigation"
            >
              <CloseIcon className="h-4 w-4" />
            </button>
            <SidebarBody
              view={view}
              onSelect={(id) => {
                onSelect(id);
                onCloseMobile();
              }}
              pipeline={pipeline}
            />
          </aside>
        </div>
      )}
    </>
  );
}
