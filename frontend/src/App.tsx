import { useState } from "react";
import {
  Activity,
  Cpu,
  History,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import type { ComponentType } from "react";
import DemoControls from "./components/DemoControls";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import LiveDashboard from "./pages/LiveDashboard";
import { useBlinkBridge } from "./hooks/useBlinkBridge";
import type { AppPage } from "./types";

const mobileNavigation: Array<{
  name: AppPage;
  Icon: ComponentType<{ size?: number; strokeWidth?: number }>;
}> = [
  { name: "Live", Icon: Activity },
  { name: "Calibration", Icon: SlidersHorizontal },
  { name: "History", Icon: History },
  { name: "Device", Icon: Cpu },
  { name: "Settings", Icon: Settings },
];

function PagePlaceholder({ page }: { page: Exclude<AppPage, "Live"> }) {
  return (
    <main className="placeholder-page">
      <p className="eyebrow">WORKSPACE</p>
      <h2>{page}</h2>
      <p>{page} is not built yet.</p>
    </main>
  );
}

export default function App() {
  const dashboard = useBlinkBridge();
  const [mobileDemoOpen, setMobileDemoOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        page={dashboard.page}
        onNavigate={dashboard.setPage}
        onSimulate={(scenario) => void dashboard.simulate(scenario)}
        simulating={dashboard.simulating}
      />
      <div className="app-main">
        <TopBar
          page={dashboard.page}
          mode={dashboard.mode}
          apiOnline={dashboard.apiOnline}
          wsState={dashboard.wsState}
          deviceStatus={dashboard.deviceStatus}
          language={dashboard.language}
          onLanguageChange={dashboard.setLanguage}
          mobileDemoOpen={mobileDemoOpen}
          onToggleDemo={() => setMobileDemoOpen((open) => !open)}
        />
        {mobileDemoOpen && (
          <div className="mobile-demo-drawer">
            <DemoControls
              active={dashboard.simulating}
              onSimulate={(scenario) => {
                setMobileDemoOpen(false);
                void dashboard.simulate(scenario);
              }}
              onClose={() => setMobileDemoOpen(false)}
            />
          </div>
        )}
        {dashboard.page === "Live" ? (
          <LiveDashboard
            sensor={dashboard.sensor}
            chartData={dashboard.chartData}
            latestCommand={dashboard.latestCommand}
            timeline={dashboard.timeline}
            stats={dashboard.stats}
            pattern={dashboard.pattern}
            patternFinalized={dashboard.patternFinalized}
            lastBlinkDuration={dashboard.lastBlinkDuration}
            deviceStatus={dashboard.deviceStatus}
            mode={dashboard.mode}
            feedback={dashboard.feedback}
            emergencyPending={dashboard.emergencyPending}
            emergency={dashboard.emergency}
            onAcknowledgeEmergency={() => void dashboard.acknowledgeEmergency()}
            onCloseEmergency={() => dashboard.dismissEmergency()}
            onHistory={() => dashboard.setPage("History")}
            apiError={dashboard.apiError}
          />
        ) : (
          <PagePlaceholder page={dashboard.page} />
        )}
      </div>
      <nav className="mobile-nav" aria-label="Primary navigation">
        {mobileNavigation.map(({ name, Icon }) => (
          <button
            aria-current={dashboard.page === name ? "page" : undefined}
            className={dashboard.page === name ? "mobile-nav-item mobile-nav-item--active" : "mobile-nav-item"}
            key={name}
            onClick={() => dashboard.setPage(name)}
            type="button"
          >
            <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            <span>{name}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}