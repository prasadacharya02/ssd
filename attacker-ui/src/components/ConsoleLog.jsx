import { useEffect, useMemo, useRef, useState } from "react";
import Card, { Button, CardHeader } from "./ui.jsx";
import { CopyIcon, DownloadIcon, SearchIcon, TerminalIcon } from "./icons.jsx";
import { cx } from "../lib/format.js";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "warn", label: "Warnings" },
  { id: "error", label: "Errors" },
];

const LEVEL_STYLE = {
  info: "text-slate-300",
  warn: "text-amber-300",
  error: "text-red-400",
  critical: "text-red-300 font-semibold",
};

function levelOf(entry) {
  return LEVEL_STYLE[entry.level] ? entry.level : "info";
}

export default function ConsoleLog({ log }) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [follow, setFollow] = useState(true);
  const [copied, setCopied] = useState(false);
  const bodyRef = useRef(null);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return log.filter((entry) => {
      const level = levelOf(entry);
      if (filter === "warn" && level !== "warn") return false;
      if (filter === "error" && level !== "error" && level !== "critical") return false;
      if (needle && !`${entry.msg}`.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [log, filter, query]);

  useEffect(() => {
    if (follow && bodyRef.current && filter === "all" && !query) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [visible.length, follow, filter, query]);

  async function copyAll() {
    const text = visible.map((entry) => `${entry.time}  ${entry.msg}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  const counts = useMemo(
    () =>
      log.reduce(
        (accumulator, entry) => {
          const level = levelOf(entry);
          accumulator[level] = (accumulator[level] || 0) + 1;
          return accumulator;
        },
        { info: 0, warn: 0, error: 0, critical: 0 },
      ),
    [log],
  );

  return (
    <Card className="flex min-h-0 flex-col p-5">
      <CardHeader label="Process console" hint={`${log.length} lines`}>
        <div className="flex items-center gap-2">
          <div className="hidden items-center rounded-md border border-slate-800 p-0.5 sm:flex">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setFilter(item.id)}
                className={cx(
                  "rounded px-2 py-1 text-[11px] font-medium transition-all duration-200",
                  filter === item.id
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                {item.label}
                {item.id === "error" && counts.error + counts.critical > 0 ? (
                  <span className="ml-1 font-mono text-red-400">
                    {counts.error + counts.critical}
                  </span>
                ) : null}
              </button>
            ))}
          </div>

          <label className="relative hidden md:block">
            <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Grep output"
              spellCheck={false}
              className="h-8 w-40 rounded-md border border-slate-800 bg-canvas/60 pl-8 pr-2 text-[12px] text-slate-200 placeholder:text-slate-500 focus:border-slate-600 focus:outline-none"
            />
          </label>

          <Button
            size="sm"
            variant="subtle"
            onClick={() => setFollow((value) => !value)}
            title="Auto-scroll to the newest line"
          >
            <span
              className={cx(
                "h-1.5 w-1.5 rounded-full",
                follow ? "bg-emerald-400" : "bg-slate-600",
              )}
            />
            Follow
          </Button>

          <Button
            size="sm"
            variant="subtle"
            icon={CopyIcon}
            onClick={copyAll}
            disabled={!visible.length}
          >
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </CardHeader>

      <div
        ref={bodyRef}
        onScroll={() => {
          const node = bodyRef.current;
          if (!node) return;
          const atBottom =
            node.scrollHeight - node.scrollTop - node.clientHeight < 24;
          if (atBottom !== follow) setFollow(atBottom);
        }}
        className="mt-4 h-[360px] min-h-0 overflow-auto rounded-md border border-slate-800 bg-black/40 p-3 font-mono text-[12px] leading-[1.6]"
      >
        {visible.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <TerminalIcon className="h-5 w-5 text-slate-600" />
            <p className="text-[12px] text-slate-500">
              {log.length
                ? "No lines match the current filter."
                : "No process output yet — execute a payload to stream the attack log."}
            </p>
          </div>
        ) : (
          visible.map((entry, index) => (
            <div key={`${entry.time}-${index}`} className="flex gap-3">
              <span className="shrink-0 tabular-nums text-slate-600">
                {entry.time || "--:--:--"}
              </span>
              <span className={cx("whitespace-pre-wrap break-words", LEVEL_STYLE[levelOf(entry)])}>
                {entry.msg}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
        <span>
          Streamed from the malware process on the victim host —{" "}
          <span className="font-mono">python -m attacker_server.ransomware_engines</span>
        </span>
        <Button size="sm" variant="subtle" icon={DownloadIcon} onClick={() => window.open("/api/log", "_blank")}>
          campaign.log
        </Button>
      </div>
    </Card>
  );
}
