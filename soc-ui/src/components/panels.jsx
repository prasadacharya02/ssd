import Card, { CardLabel } from "./Card.jsx";
import { cx, formatFloat, formatInt, shortHash } from "../lib/format.js";
import { CpuIcon, LedgerIcon } from "./icons.jsx";

/** Verdict + reasoning for the most recent pipeline decision. */
export function DecisionPanel({ decision }) {
  const verdict = decision?.decision ?? "—";
  const confidence = Number(decision?.confidence ?? 0);
  const hostile = verdict !== "STANDBY" && verdict !== "IGNORE";

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardLabel>Last decision</CardLabel>
        <span className="inline-flex items-center gap-1.5 rounded border border-slate-800 bg-canvas/60 px-2 py-1 font-mono text-[10px] uppercase tracking-wide text-slate-400">
          <CpuIcon className="h-3 w-3" />
          {decision?.engine ?? "rules"}
        </span>
      </div>

      <p
        className={cx(
          "mt-4 text-xl font-semibold tracking-tight",
          hostile ? "text-red-400" : "text-slate-100",
        )}
      >
        {verdict}
      </p>

      <div className="mt-4">
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>Model confidence</span>
          <span className="tabular-nums">{formatFloat(confidence, 1)}%</span>
        </div>
        <div className="mt-2 h-1 rounded-full bg-slate-800">
          <div
            className={cx(
              "h-1 rounded-full transition-all duration-200",
              hostile ? "bg-red-400" : "bg-slate-400",
            )}
            style={{ width: `${Math.min(100, Math.max(0, confidence))}%` }}
          />
        </div>
      </div>

      {Array.isArray(decision?.factors) && decision.factors.length > 0 && (
        <ul className="mt-5 space-y-2 border-t border-slate-800 pt-4">
          {decision.factors.slice(0, 4).map((factor, index) => (
            <li
              key={index}
              className="flex items-center justify-between gap-4 text-[12px]"
            >
              <span className="text-slate-500">{factor.name}</span>
              <span className="truncate font-medium text-slate-300">
                {factor.value}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Blockchain / audit ledger status. */
export function LedgerPanel({ ledger }) {
  const connected = Boolean(ledger?.connected);
  const onChain = Boolean(ledger?.is_blockchain);

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardLabel>Evidence ledger</CardLabel>
        <LedgerIcon className="h-4 w-4 text-slate-500" />
      </div>

      <p className="mt-4 text-sm font-medium leading-relaxed text-slate-200">
        {ledger?.mode_label ?? "Ledger unavailable"}
      </p>

      <dl className="mt-4 space-y-2 border-t border-slate-800 pt-4 text-[12px]">
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Entries anchored</dt>
          <dd className="font-semibold tabular-nums text-slate-200">
            {formatInt(ledger?.tx_count)}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Backend</dt>
          <dd className="text-slate-300">{onChain ? "Smart contract" : "Local ledger"}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Contract</dt>
          <dd className="font-mono text-slate-300">{shortHash(ledger?.address)}</dd>
        </div>
      </dl>

      <span
        className={cx(
          "mt-4 inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-[11px] font-medium",
          connected
            ? "border-slate-800 text-slate-300"
            : "border-slate-800 text-slate-500",
        )}
      >
        <span
          className={cx(
            "h-1.5 w-1.5 rounded-full",
            connected ? "bg-emerald-400" : "bg-slate-600",
          )}
        />
        {connected ? "Verifier reachable" : "Verifier unreachable"}
      </span>
    </Card>
  );
}
