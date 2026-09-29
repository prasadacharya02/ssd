import { useEffect, useState } from "react";
import { io } from "socket.io-client";

/** Polling intervals in ms. Socket.io is primary; polling is the safety net. */
const INTERVALS = {
  stats: 6000,
  threat: 6000,
  decision: 6000,
  ledger: 12000,
  entropy: 8000,
  entropyConfig: 30000,
  processes: 10000,
};

async function getJSON(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

function usePoll(url, interval) {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    let timer;

    const load = async () => {
      try {
        const payload = await getJSON(url);
        if (!alive) return;
        setData(payload);
        setFailed(false);
      } catch {
        if (alive) setFailed(true);
      }
    };

    load();
    timer = setInterval(load, interval);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [url, interval]);

  return [data, failed];
}

/**
 * Central data source for the SOC view: REST polling plus the Socket.IO
 * stream the Flask backend already emits (`live_update`, `new_event`).
 */
export function useSocData() {
  const [stats] = usePoll("/api/stats", INTERVALS.stats);
  const [threat] = usePoll("/api/threat-level", INTERVALS.threat);
  const [decision] = usePoll("/api/dqn/last", INTERVALS.decision);
  const [ledger] = usePoll("/api/blockchain/status", INTERVALS.ledger);
  const [entropy] = usePoll("/api/entropy", INTERVALS.entropy);
  const [entropyConfig] = usePoll("/api/entropy/config", INTERVALS.entropyConfig);
  const [processes] = usePoll("/api/processes", INTERVALS.processes);
  const [pipeline, pipelineDown] = usePoll("/api/pipeline", 5000);

  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [lastSync, setLastSync] = useState(null);

  /**
   * The live entropy series the chart draws. Built from ONE merged,
   * de-duplicated stream (keyed by the event row id):
   *   1. the /api/entropy poll (backfill + safety net), and
   *   2. the sub-second `new_event` socket pushes (the live feed).
   * Every point is a real pipeline detection value — the exact entropy
   * reading the decision engine acted on. Nothing is synthesized.
   */
  const [entropySeries, setEntropySeries] = useState([]);

  const mergeEntropy = (rows) => {
    if (!Array.isArray(rows) || rows.length === 0) return;
    setEntropySeries((prev) => {
      const byId = new Map(prev.map((p) => [p.id, p]));
      for (const row of rows) {
        if (row && row.id != null && Number.isFinite(Number(row.entropy))) {
          byId.set(row.id, row);
        }
      }
      return [...byId.values()].sort((a, b) => a.id - b.id).slice(-90);
    });
  };

  // Merge the polled backfill into the series whenever it refreshes.
  useEffect(() => {
    mergeEntropy(entropy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entropy]);

  // Initial incident feed.
  useEffect(() => {
    let alive = true;
    getJSON("/api/events")
      .then((rows) => alive && setEvents(rows))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Live stream.
  useEffect(() => {
    const socket = io({ transports: ["websocket", "polling"] });

    socket.on("connect", () => setConnected(true));
    socket.on("disconnect", () => setConnected(false));

    socket.on("live_update", (payload) => {
      setLastSync(payload?.time || new Date().toLocaleTimeString("en-GB"));
    });

    socket.on("new_event", (row) => {
      if (!row) return;
      setEvents((prev) => {
        if (prev.some((e) => e.id === row.id)) return prev;
        return [row, ...prev].slice(0, 50);
      });
      // The same event the detector produced feeds the live graph as
      // it happens — GRAPH VALUE = ACTUAL DETECTION VALUE.
      mergeEntropy([row]);
    });

    return () => socket.disconnect();
  }, []);

  return {
    stats,
    threat,
    decision,
    ledger,
    entropy,
    entropySeries,
    entropyConfig,
    processes,
    pipeline,
    pipelineDown,
    events,
    connected,
    lastSync,
  };
}
