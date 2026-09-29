import Card from "../components/Card.jsx";

/**
 * Clinical placeholder for modules that are wired in later phases.
 * Honest about status — no fake data.
 */
export default function EmptyModule({ title, description, onBack }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-100">
          {title}
        </h1>
        <p className="mt-1 text-[13px] text-slate-500">{description}</p>
      </div>

      <Card className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-slate-800 bg-canvas/60">
          <span className="h-2 w-2 rounded-full bg-slate-600" />
        </div>
        <p className="mt-5 text-sm font-medium text-slate-200">
          Module not yet connected
        </p>
        <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-slate-500">
          This workspace is part of the next rollout phase. Detection, response,
          and ledger data remain available under Incidents.
        </p>
        <button
          type="button"
          onClick={onBack}
          className="mt-6 rounded-md border border-slate-700 bg-slate-800/60 px-4 py-2 text-[13px] font-medium text-slate-100 transition-all duration-200 hover:border-slate-600 hover:bg-slate-800"
        >
          Back to Incidents
        </button>
      </Card>
    </div>
  );
}
