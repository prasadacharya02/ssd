import { useEffect, useState } from "react";
import { clockOf, cx } from "../lib/format.js";
import { links } from "../lib/console-config.js";
import { Chip, StatusDot } from "./ui.jsx";
import { CrosshairIcon, ExternalIcon, ShieldIcon, ServerIcon } from "./icons.jsx";

function BrandMark() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-md border border-amber-500/30 bg-amber-500/10">
      <CrosshairIcon className="h-4 w-4 text-amber-300" />
    </div>
  );
}

function QuickLink({ href, label, icon: Icon }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-800 bg-panel px-2.5 text-[12px] font-medium text-slate-400 transition-all duration-200 hover:border-slate-700 hover:text-slate-200"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
      <ExternalIcon className="h-3 w-3 opacity-60" />
    </a>
  );
}

function WallClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <span className="hidden font-mono text-[12px] tabular-nums text-slate-400 sm:inline">
      {clockOf(now)}
    </span>
  );
}

export default function TopBar({ connected, running }) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-canvas/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <BrandMark />
          <div className="leading-tight">
            <p className="text-[15px] font-semibold tracking-tight text-slate-100">
              Entropy
            </p>
            <p className="text-[11px] text-slate-500">Attacker Operator Console</p>
          </div>
        </div>

        <Chip tone="amber" className="ml-2 hidden md:inline-flex">
          <ShieldIcon className="h-3.5 w-3.5" />
          Sandboxed lab · fixtures only
        </Chip>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <div className="hidden items-center gap-2 lg:flex">
            <QuickLink href={links.victim} label="Victim PC" icon={ServerIcon} />
            <QuickLink href={links.dashboard} label="SOC" icon={ShieldIcon} />
          </div>

          <Chip tone={connected ? "emerald" : "slate"} className="hidden sm:inline-flex">
            <StatusDot
              tone={connected ? "emerald" : "slate"}
              pulse={connected && running}
            />
            {connected ? "Service online" : "Service unreachable"}
          </Chip>

          <span className={cx("h-6 w-px bg-slate-800")} />
          <WallClock />
        </div>
      </div>
    </header>
  );
}
