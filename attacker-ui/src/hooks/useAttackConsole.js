import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api.js";

const STATS_INTERVAL = 800;
const TARGETS_INTERVAL = 4000;

const PHASE_LABEL = {
  IDLE: "Idle",
  SCANNING: "Scanning estate",
  ENCRYPTING: "Encrypting files",
  FINALIZING: "Finalizing",
  PAUSED: "Paused by operator",
  KILLED_BY_DEFENDER: "Terminated by defender",
  COMPLETED: "Run complete",
  STOPPED: "Stopped by operator",
};

export function phaseLabel(phase) {
  return PHASE_LABEL[phase] || phase || "Idle";
}

/**
 * Single source of truth for the operator console.
 *
 * Polls the attacker service (REST, same origin), tracks connectivity, and
 * observes phase transitions locally so the kill-chain timeline reflects what
 * this console actually saw — never inferred history the backend never sent.
 */
export function useAttackConsole() {
  const [families, setFamilies] = useState([]);
  const [stats, setStats] = useState(null);
  const [targets, setTargets] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  const phaseRef = useRef(null);
  const runRef = useRef(null);
  const mounted = useRef(true);

  const loadStats = useCallback(async () => {
    try {
      const payload = await api.stats();
      if (!mounted.current) return;
      setStats(payload);
      setConnected(true);
    } catch {
      if (mounted.current) setConnected(false);
    }
  }, []);

  const loadTargets = useCallback(async () => {
    try {
      const payload = await api.targets();
      if (mounted.current) setTargets(payload);
    } catch {
      /* estate preview is best effort; telemetry stays authoritative */
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    api
      .families()
      .then((payload) => mounted.current && setFamilies(payload || []))
      .catch(() => mounted.current && setFamilies([]));
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    loadStats();
    const timer = setInterval(loadStats, STATS_INTERVAL);
    return () => clearInterval(timer);
  }, [loadStats]);

  useEffect(() => {
    loadTargets();
    const timer = setInterval(loadTargets, TARGETS_INTERVAL);
    return () => clearInterval(timer);
  }, [loadTargets]);

  /* ── Observed phase transitions ───────────────────────────── */
  useEffect(() => {
    if (!stats) return;
    const phase = stats.phase || "IDLE";
    const runId = stats.started_at || stats.pid || null;

    if (phaseRef.current === null) {
      phaseRef.current = phase;
      return;
    }
    if (phase === phaseRef.current && runId === runRef.current) return;

    const previous = phaseRef.current;
    phaseRef.current = phase;
    runRef.current = runId;

    // A new run starts from the top; keep the timeline tied to this run only.
    const startsRun = phase === "SCANNING" && previous === "IDLE";

    setTimeline((entries) => {
      const next = [
        {
          id: `${entries.length}-${phase}-${Date.now()}`,
          phase,
          previous: startsRun ? null : previous,
          at: new Date(),
          hit: stats.files_hit ?? 0,
          targets: stats.targets ?? 0,
        },
        ...(startsRun ? [] : entries),
      ];
      return next.slice(0, 14);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats?.phase, stats?.started_at, stats?.pid]);

  /* ── Operator actions ─────────────────────────────────────── */
  const run = useCallback(
    async (name, fn) => {
      setBusy(name);
      setError("");
      try {
        const result = await fn();
        await Promise.all([loadStats(), loadTargets()]);
        return result;
      } catch (exception) {
        if (mounted.current) {
          setError(exception?.message || "request failed");
        }
        return null;
      } finally {
        if (mounted.current) setBusy(null);
      }
    },
    [loadStats, loadTargets],
  );

  const actions = useMemo(
    () => ({
      launch: (family) => run("launch", () => api.launch(family)),
      stop: () => run("stop", () => api.stop()),
      pause: () => run("pause", () => api.pause()),
      resume: () => run("resume", () => api.resume()),
      speed: (factor) => run("speed", () => api.speed(factor)),
      reset: () => run("reset", () => api.reset()),
    }),
    [run],
  );

  const clearTimeline = useCallback(() => setTimeline([]), []);
  const dismissError = useCallback(() => setError(""), []);

  return {
    families,
    stats,
    targets,
    timeline,
    connected,
    error,
    busy,
    actions,
    refresh: { stats: loadStats, targets: loadTargets },
    clearTimeline,
    dismissError,
  };
}
