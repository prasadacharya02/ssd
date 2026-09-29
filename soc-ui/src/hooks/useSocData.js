import { useEffect, useState } from "react";
import { io } from "socket.io-client";

/** Polling intervals in ms. Socket.io is primary; polling is the safety net. */
const INTERVALS = {
  stats: 6000,
  threat: 6000,
  decision: 6000,
  ledger: 12000,
  entropy: 8000,
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
  const [processes] = usePoll("/api/processes", INTERVALS.processes);
  const [pipeline, pipelineDown] = usePoll("/api/pipeline", 5000);

  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [lastSync, setLastSync] = useState(null);

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
    });

    return () => socket.disconnect();
  }, []);

  return {
    stats,
    threat,
    decision,
    ledger,
    entropy,
    processes,
    pipeline,
    pipelineDown,
    events,
    connected,
    lastSync,
  };
}
