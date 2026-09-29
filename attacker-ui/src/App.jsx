import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "./components/TopBar.jsx";
import PayloadCatalog from "./components/PayloadCatalog.jsx";
import CommandDeck from "./components/CommandDeck.jsx";
import KillChain from "./components/KillChain.jsx";
import EstateSnapshot from "./components/EstateSnapshot.jsx";
import ConsoleLog from "./components/ConsoleLog.jsx";
import { Chip, StatusDot, CardLabel } from "./components/ui.jsx";
import { AlertIcon, CloseIcon, ShieldIcon } from "./components/icons.jsx";
import { useAttackConsole } from "./hooks/useAttackConsole.js";
import { deriveRun, estateFrom } from "./lib/derive.js";
import { links } from "./lib/console-config.js";
import { formatInt } from "./lib/format.js";

const DEFAULT_FAMILY = "wannacry";

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

function Notice({ tone = "slate", title, children, onDismiss, icon: Icon }) {
  const tones = {
    slate: "border-slate-800 bg-panel text-slate-300",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    red: "border-red-500/30 bg-red-500/10 text-red-200",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  };
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${tones[tone]}`}
      role="status"
    >
      {Icon ? <Icon className="mt-0.5 h-4 w-4 shrink-0" /> : null}
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium">{title}</p>
        <p className="mt-0.5 text-[12px] leading-relaxed opacity-80">{children}</p>
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded p-1 opacity-60 transition-opacity duration-200 hover:opacity-100"
          aria-label="Dismiss"
        >
          <CloseIcon className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>
  );
}

export default function App() {
  const {
    families,
    stats,
    targets,
    timeline,
    connected,
    error,
    busy,
    actions,
    clearTimeline,
    dismissError,
  } = useAttackConsole();

  const [selected, setSelected] = useState(null);
  const run = useMemo(() => deriveRun(stats), [stats]);
  const estate = useMemo(() => estateFrom(targets, stats?.victim), [targets, stats]);

  const selectedFamily = useMemo(() => {
    if (!families.length) return null;
    return (
      families.find((family) => family.id === selected) ||
      families.find((family) => family.id === DEFAULT_FAMILY) ||
      families[0]
    );
  }, [families, selected]);

  useEffect(() => {
    if (!selected && families.length) {
      const preferred =
        families.find((family) => family.id === DEFAULT_FAMILY) || families[0];
      setSelected(preferred.id);
    }
  }, [families, selected]);

  const onSpeed = useCallback(
    (factor) => {
      actions.speed(factor);
    },
    [actions],
  );

  /* Operator keyboard shortcuts — never fire while typing in a field. */
  useEffect(() => {
    function onKeyDown(event) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isTypingTarget(event.target)) return;

      const key = event.key.toLowerCase();
      if (key === "x" && run.active) {
        event.preventDefault();
        actions.stop();
      } else if (key === "p" && run.active) {
        event.preventDefault();
        run.paused ? actions.resume() : actions.pause();
      } else if (/^[0-9]$/.test(key)) {
        const index = key === "0" ? 9 : Number(key) - 1;
        const family = families[index];
        if (family) setSelected(family.id);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actions, families, run.active, run.paused]);

  const lastEntry = timeline[0];

  return (
    <div className="min-h-screen bg-canvas">
      <TopBar connected={connected} running={run.active} />

      <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:py-8">
        <div className="grid gap-6 xl:grid-cols-12">
          <aside className="space-y-6 xl:col-span-4">
            <div className="xl:sticky xl:top-20 xl:h-[calc(100vh-7rem)]">
              <PayloadCatalog
                families={families}
                selected={selectedFamily?.id}
                onSelect={setSelected}
                locked={run.active}
                hint={
                  run.active
                    ? "Payload switching is locked while a campaign process is running."
                    : undefined
                }
              />
            </div>
          </aside>

          <div className="space-y-6 xl:col-span-8">
            {error ? (
              <Notice tone="red" title="Control request rejected" icon={AlertIcon} onDismiss={dismissError}>
                {error}
              </Notice>
            ) : null}

            {run.defenderKilled ? (
              <Notice tone="emerald" title="Defense won this run" icon={ShieldIcon}>
                The ENTROPY pipeline attributed the open file handle to pid{" "}
                <span className="font-mono">{run.pid ?? "—"}</span> and terminated the
                process (exit {run.exitCode ?? 42}). {formatInt(run.counters.hit)} of{" "}
                {formatInt(run.counters.targets)} staged files were overwritten before
                the kill — {formatInt(run.counters.remaining)} were never touched.{" "}
                <a
                  href={links.dashboard}
                  target="_blank"
                  rel="noreferrer"
                  className="underline decoration-emerald-400/40 underline-offset-2"
                >
                  Open the SOC feed
                </a>{" "}
                for the detection timeline.
              </Notice>
            ) : null}

            {!run.defenderKilled && run.phase === "COMPLETED" ? (
              <Notice tone="amber" title="Run completed without interception" icon={AlertIcon}>
                {formatInt(run.counters.hit)} of {formatInt(run.counters.targets)} files
                were overwritten and ransom notes dropped. Restore the estate before the
                next demo run so the SOC feed starts from a clean baseline.
              </Notice>
            ) : null}

            {estate.locked > 0 ? (
              <Notice tone="slate" title="Estate is dirty" icon={AlertIcon}>
                {formatInt(estate.locked)} locked file(s) and {formatInt(estate.notes)}{" "}
                ransom note(s) are still on disk. Use{" "}
                <span className="font-medium text-slate-200">Restore estate</span> to
                rewrite the clean fixture baseline.
              </Notice>
            ) : null}

            <CommandDeck
              family={selectedFamily}
              run={run}
              busy={busy}
              onLaunch={(familyId) => {
                clearTimeline();
                actions.launch(familyId);
              }}
              onStop={actions.stop}
              onPause={actions.pause}
              onResume={actions.resume}
              onSpeed={onSpeed}
              onReset={actions.reset}
              onExport={() => window.open("/api/log", "_blank")}
            />

            <div className="grid gap-6 lg:grid-cols-2">
              <KillChain timeline={timeline} run={run} onClear={clearTimeline} />
              <EstateSnapshot
                estate={estate}
                familyExtension={selectedFamily?.extension}
              />
            </div>

            <ConsoleLog log={run.log} />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-4 text-[11px] text-slate-500 sm:px-6">
          <span className="inline-flex items-center gap-2">
            <StatusDot tone={connected ? "emerald" : "slate"} pulse={connected && run.active} />
            {connected
              ? lastEntry
                ? `Last transition: ${lastEntry.phase} at ${lastEntry.at.toLocaleTimeString("en-GB", { hour12: false })}`
                : "Console polling the attacker service every 800 ms"
              : "Attacker service unreachable"}
          </span>

          <span className="hidden h-3 w-px bg-slate-800 sm:block" />

          <span className="inline-flex items-center gap-2">
            <CardLabel className="text-slate-500">Shortcuts</CardLabel>
            <Chip className="px-1.5 py-0.5 font-mono">1–9 select</Chip>
            <Chip className="px-1.5 py-0.5 font-mono">P pause</Chip>
            <Chip className="px-1.5 py-0.5 font-mono">X abort</Chip>
          </span>

          <span className="ml-auto hidden items-center gap-2 md:inline-flex">
            <ShieldIcon className="h-3.5 w-3.5" />
            Controlled simulation · fixtures overwritten, never real user data
          </span>
        </div>
      </footer>
    </div>
  );
}
