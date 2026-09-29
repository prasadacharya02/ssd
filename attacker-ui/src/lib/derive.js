/** Presentation-safe derivations from the attacker service stats payload. */

import { percent } from "./format.js";

export const RUN_PHASES = [
  "IDLE",
  "SCANNING",
  "ENCRYPTING",
  "FINALIZING",
  "PAUSED",
  "STOPPED",
  "COMPLETED",
  "KILLED_BY_DEFENDER",
];

/**
 * Phase -> tone. "KILLED_BY_DEFENDER" is deliberately the positive tone:
 * on this lab the defender winning is the expected, correct outcome.
 */
const PHASE_TONE = {
  IDLE: "slate",
  SCANNING: "sky",
  ENCRYPTING: "red",
  FINALIZING: "amber",
  PAUSED: "amber",
  STOPPED: "slate",
  COMPLETED: "slate",
  KILLED_BY_DEFENDER: "emerald",
};

export function phaseTone(phase) {
  return PHASE_TONE[phase] || "slate";
}

export function deriveRun(stats) {
  const source = stats || {};
  const phase = source.phase || "IDLE";
  const active = Boolean(source.active);
  const paused = Boolean(source.paused) || phase === "PAUSED";
  const defenderKilled = Boolean(source.defender_killed);
  const targets = Number(source.targets) || 0;
  const hit = Number(source.files_hit) || 0;

  return {
    phase,
    tone: phaseTone(phase),
    active,
    paused,
    defenderKilled,
    family: source.family || null,
    pid: source.pid ?? null,
    exitCode: source.exit_code ?? source.returncode ?? null,
    progress: percent(source.progress ?? (targets ? (hit / targets) * 100 : 0)),
    counters: {
      targets,
      hit,
      skipped: Number(source.files_skipped) || 0,
      notes: Number(source.notes_dropped) || 0,
      bytes: Number(source.bytes_encrypted) || 0,
      remaining: Math.max(0, targets - hit),
    },
    rate: Number(source.files_per_second) || 0,
    elapsed: Number(source.elapsed_seconds) || 0,
    startedAt: source.started_at || null,
    finishedAt: source.finished_at || null,
    log: Array.isArray(source.log) ? source.log : [],
    speed: Number(source.speed_factor) || 1,
  };
}

/** True once the child process has produced any output at all. */
export function hasRun(stats) {
  const run = deriveRun(stats);
  return Boolean(run.family) || run.log.length > 0 || run.phase !== "IDLE";
}

export function estateFrom(targets, victim) {
  const source = targets || {};
  return {
    exists: source.exists ?? Boolean(victim?.exists),
    total: source.total ?? victim?.total ?? 0,
    bytes: source.bytes ?? 0,
    folders: Array.isArray(source.folders) ? source.folders : [],
    extensions: Array.isArray(source.extensions) ? source.extensions : [],
    attackable: source.attackable ?? source.total ?? 0,
    locked: victim?.locked ?? source.locked ?? 0,
    notes: victim?.notes ?? source.notes ?? 0,
    evidence: source.quarantine_evidence ?? 0,
    backedUp: source.backed_up ?? 0,
  };
}
