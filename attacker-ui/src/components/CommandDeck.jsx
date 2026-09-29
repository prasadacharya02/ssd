import { useEffect, useRef, useState } from "react";
import Card, { Button, CardLabel, Chip, ProgressBar, StatTile } from "./ui.jsx";
import {
  BoltIcon,
  DownloadIcon,
  FileIcon,
  PauseIcon,
  PlayIcon,
  ResetIcon,
  ShieldIcon,
  StopIcon,
} from "./icons.jsx";
import {
  cx,
  formatBytes,
  formatDuration,
  formatFloat,
  formatInt,
  percent,
} from "../lib/format.js";

const SPEED_PRESETS = [0.5, 1, 2, 5];
const ARM_WINDOW_MS = 4000;

const PHASE_COPY = {
  IDLE: "No campaign running. Select a payload and execute to begin.",
  SCANNING: "Enumerating the victim estate and staging the target list.",
  ENCRYPTING: "Overwriting target files and holding each handle open.",
  FINALIZING: "Encryption pass complete — dropping ransom notes and exiting.",
  PAUSED: "Paused by operator. The process is idle but still resident.",
  STOPPED: "Stopped by operator (SIGINT). Clean exit, no kill signal from defense.",
  COMPLETED: "Run finished: every staged target was overwritten.",
  KILLED_BY_DEFENDER:
    "The ENTROPY pipeline attributed the open file handle to this PID and terminated it (exit 42). Remaining targets were never touched.",
};

function SpeedControl({ speed, onChange, disabled }) {
  const [local, setLocal] = useState(speed ?? 1);

  useEffect(() => {
    if (speed && Math.abs(speed - local) > 0.001) setLocal(speed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
        <BoltIcon className="h-3.5 w-3.5" />
        Rate
      </span>
      <input
        type="range"
        min="0.1"
        max="5"
        step="0.1"
        value={local}
        disabled={disabled}
        onChange={(event) => setLocal(Number(event.target.value))}
        onMouseUp={() => onChange(local)}
        onTouchEnd={() => onChange(local)}
        onKeyUp={() => onChange(local)}
        className="min-w-[140px] flex-1 disabled:opacity-40"
        aria-label="Encryption rate multiplier"
      />
      <span className="w-12 font-mono text-[12px] tabular-nums text-slate-300">
        {formatFloat(local, 1)}×
      </span>
      <div className="flex items-center gap-1">
        {SPEED_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            disabled={disabled}
            onClick={() => {
              setLocal(preset);
              onChange(preset);
            }}
            className={cx(
              "h-7 rounded-md border px-2 font-mono text-[11px] transition-all duration-200",
              Math.abs(local - preset) < 0.05
                ? "border-slate-700 bg-slate-800/70 text-slate-200"
                : "border-slate-800 text-slate-500 hover:text-slate-300",
              disabled && "cursor-not-allowed opacity-40",
            )}
          >
            {preset}×
          </button>
        ))}
      </div>
    </div>
  );
}

export default function CommandDeck({
  family,
  run,
  busy,
  onLaunch,
  onStop,
  onPause,
  onResume,
  onSpeed,
  onReset,
  onExport,
}) {
  const [armed, setArmed] = useState(false);
  const disarmTimer = useRef(null);

  useEffect(() => () => clearTimeout(disarmTimer.current), []);
  useEffect(() => {
    if (!run.active) setArmed(false);
  }, [run.active]);

  if (!family) {
    return (
      <Card>
        <CardLabel>Campaign control</CardLabel>
        <p className="mt-4 text-[13px] text-slate-500">
          Loading payload catalog from the attacker service…
        </p>
      </Card>
    );
  }

  const toneChip = {
    slate: "slate",
    sky: "sky",
    amber: "amber",
    red: "red",
    emerald: "emerald",
  }[run.tone];

  const launchDisabled = run.active || Boolean(busy);

  function handleLaunch() {
    if (!armed) {
      setArmed(true);
      clearTimeout(disarmTimer.current);
      disarmTimer.current = setTimeout(() => setArmed(false), ARM_WINDOW_MS);
      return;
    }
    clearTimeout(disarmTimer.current);
    setArmed(false);
    onLaunch(family.id);
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardLabel>Campaign control</CardLabel>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="text-[20px] font-semibold tracking-tight text-slate-100">
              {family.name}
            </h2>
            <span className="font-mono text-[12px] text-amber-300">
              {family.extension}
            </span>
          </div>
          <p className="mt-1 text-[12px] text-slate-500">
            note {family.note} · {family.speed} · {family.style}
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <Chip tone={toneChip}>
            <ShieldIcon className="h-3.5 w-3.5" />
            {run.phase.replaceAll("_", " ")}
          </Chip>
          <span className="font-mono text-[11px] tabular-nums text-slate-500">
            {run.active ? `pid ${run.pid ?? "—"}` : `exit ${run.exitCode ?? "—"}`}
          </span>
        </div>
      </div>

      <p className="mt-3 text-[13px] leading-relaxed text-slate-400">
        {PHASE_COPY[run.phase] || "Campaign in progress."}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button
          variant={armed ? "armed" : "primary"}
          icon={PlayIcon}
          onClick={handleLaunch}
          disabled={launchDisabled}
          title="Launch the selected payload as a separate OS process"
        >
          {armed ? `Confirm ${family.short_name || family.name} launch` : "Execute payload"}
        </Button>
        <Button
          icon={PauseIcon}
          onClick={run.paused ? onResume : onPause}
          disabled={!run.active || Boolean(busy)}
        >
          {run.paused ? "Resume" : "Pause"}
        </Button>
        <Button
          variant="default"
          icon={StopIcon}
          onClick={onStop}
          disabled={!run.active || Boolean(busy)}
          title="Operator stop: SIGINT, clean exit"
        >
          Abort
        </Button>
        <Button
          icon={ResetIcon}
          onClick={onReset}
          disabled={Boolean(busy)}
          title="Restore the victim fixture estate from the clean baseline"
        >
          Restore estate
        </Button>
        <Button variant="subtle" icon={DownloadIcon} onClick={onExport}>
          Export log
        </Button>
      </div>

      <div className="mt-4 border-t border-slate-800 pt-4">
        <SpeedControl speed={run.speed} onChange={onSpeed} disabled={!run.active} />
      </div>

      <div className="mt-4 border-t border-slate-800 pt-4">
        <div className="flex items-baseline justify-between">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
            <FileIcon className="h-3.5 w-3.5" />
            Progress
          </span>
          <span className="font-mono text-[12px] tabular-nums text-slate-400">
            {formatInt(run.counters.hit)} / {formatInt(run.counters.targets)} staged
            {" · "}
            {formatFloat(percent(run.progress), 0)}%
            {run.elapsed ? ` · ${formatDuration(run.elapsed)}` : ""}
          </span>
        </div>
        <ProgressBar
          value={run.progress}
          tone={run.defenderKilled ? "emerald" : run.tone === "sky" ? "amber" : "red"}
          className="mt-2"
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Staged" value={formatInt(run.counters.targets)} tone="muted" />
        <StatTile label="Encrypted" value={formatInt(run.counters.hit)} tone="red" />
        <StatTile label="Skipped" value={formatInt(run.counters.skipped)} tone="muted" />
        <StatTile label="Notes" value={formatInt(run.counters.notes)} tone="amber" />
        <StatTile label="Bytes" value={formatBytes(run.counters.bytes)} tone="muted" />
        <StatTile
          label="Obs. rate"
          value={formatFloat(run.rate, 2)}
          unit="files/s"
          tone="muted"
        />
      </div>
    </Card>
  );
}
