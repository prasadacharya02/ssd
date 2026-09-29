import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import IncidentsView from "./views/IncidentsView.jsx";
import EmptyModule from "./views/EmptyModule.jsx";
import { useSocData } from "./hooks/useSocData.js";

const MODULES = {
  hunting: {
    title: "Threat Hunting",
    description:
      "Query historical entropy readings and verdicts across the event store.",
  },
  assets: {
    title: "Assets",
    description:
      "Monitored folders, decoy files, and the health of each watched endpoint.",
  },
  settings: {
    title: "Settings",
    description:
      "Detection thresholds, response policy, ledger backend, and dry-run controls.",
  },
};

export default function App() {
  const [view, setView] = useState("incidents");
  const [query, setQuery] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const data = useSocData();

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar
        view={view}
        onSelect={setView}
        pipeline={data.pipeline}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div className="min-w-0 flex-1">
        <TopBar
          query={query}
          onQueryChange={setQuery}
          connected={data.connected}
          alertCount={data.stats?.threats ?? 0}
          onOpenMobile={() => setMobileOpen(true)}
        />

        <main className="mx-auto max-w-[1320px] px-4 py-6 sm:px-6 lg:py-8">
          {view === "incidents" ? (
            <IncidentsView data={data} query={query} />
          ) : (
            <EmptyModule {...MODULES[view]} onBack={() => setView("incidents")} />
          )}
        </main>
      </div>
    </div>
  );
}
