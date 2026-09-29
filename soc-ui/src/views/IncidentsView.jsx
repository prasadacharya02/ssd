import MetricBoard from "../components/MetricBoard.jsx";
import IncidentTable from "../components/IncidentTable.jsx";
import { DecisionPanel, LedgerPanel } from "../components/panels.jsx";
import { ClockIcon } from "../components/icons.jsx";

function PageHeader({ lastSync, onExport }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-100">
          Incidents
        </h1>
        <p className="mt-1 text-[13px] text-slate-500">
          Live detection and response posture across the monitored estate.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-md border border-slate-800 bg-panel px-3 py-1.5 text-xs text-slate-400">
          <ClockIcon className="h-3.5 w-3.5" />
          {lastSync ? `Synced ${lastSync}` : "Waiting for first sync"}
        </span>
        <button
          type="button"
          onClick={onExport}
          className="rounded-md border border-slate-800 bg-panel px-3 py-1.5 text-xs font-medium text-slate-200 transition-all duration-200 hover:border-slate-600 hover:bg-slate-800/60"
        >
          Export report
        </button>
      </div>
    </div>
  );
}

export default function IncidentsView({ data, query }) {
  const exportFeed = () => {
    const blob = new Blob([JSON.stringify(data.events, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `entropy-incidents-${new Date().toISOString().slice(0, 19)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <PageHeader lastSync={data.lastSync} onExport={exportFeed} />
      <MetricBoard stats={data.stats} threat={data.threat} entropy={data.entropy} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <IncidentTable events={data.events} query={query} onExport={exportFeed} />
        <div className="space-y-6">
          <DecisionPanel decision={data.decision} />
          <LedgerPanel ledger={data.ledger} />
        </div>
      </div>

    </div>
  );
}
