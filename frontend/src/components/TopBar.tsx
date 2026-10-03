import { ChevronDown, Radio, Wifi, WifiOff } from "lucide-react";
import type { AppPage, DeviceStatus, Language } from "../types";

interface TopBarProps {
  page: AppPage;
  mode: "live" | "demo";
  apiOnline: boolean;
  wsState: "connecting" | "connected" | "reconnecting";
  deviceStatus: DeviceStatus | null;
  language: Language;
  onLanguageChange: (language: Language) => void;
  mobileDemoOpen: boolean;
  onToggleDemo: () => void;
}

const languageNames: Array<{ id: Language; label: string }> = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिंदी" },
  { id: "mr", label: "मराठी" },
];

export default function TopBar({
  page,
  mode,
  apiOnline,
  wsState,
  deviceStatus,
  language,
  onLanguageChange,
  mobileDemoOpen,
  onToggleDemo,
}: TopBarProps) {
  const deviceLabel =
    mode === "demo"
      ? "Simulated feed"
      : deviceStatus?.status === "ONLINE"
        ? "Device connected"
        : "Device offline";
  const wsLabel =
    wsState === "connected"
      ? "WebSocket connected"
      : wsState === "reconnecting"
        ? "Reconnecting…"
        : "Connecting…";

  return (
    <header className="topbar">
      <div className="topbar-title-wrap">
        <h1 className="topbar-title">{page === "Live" ? "Live dashboard" : page}</h1>
        <button
          aria-expanded={mobileDemoOpen}
          className="mobile-demo-toggle"
          onClick={onToggleDemo}
          type="button"
        >
          Demo controls <ChevronDown size={20} strokeWidth={1.75} />
        </button>
      </div>

      <div className="topbar-tools">
        <span
          className={`status-badge ${apiOnline ? "status-badge--ok" : "status-badge--warn"}`}
          title={apiOnline ? "Backend API is responding" : "Backend API is unavailable"}
        >
          <Radio size={20} strokeWidth={1.75} aria-hidden="true" />
          <span>{apiOnline ? deviceLabel : "API offline"}</span>
        </span>
        <span className={`mode-badge mode-badge--${mode}`}>
          <span className="mode-dot" />
          {mode === "demo" ? "Demo mode" : "Live hardware"}
        </span>
        {mode === "demo" && deviceStatus?.battery !== null && deviceStatus?.battery !== undefined && (
          <span className="battery-label">
            Battery {Math.round(deviceStatus.battery)}% <b>SIMULATED</b>
          </span>
        )}

        <div className="language-control" aria-label="Message language">
          {languageNames.map(({ id, label }) => (
            <button
              aria-pressed={language === id}
              className={language === id ? "language-option language-option--active" : "language-option"}
              key={id}
              onClick={() => onLanguageChange(id)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        <span
          aria-live="polite"
          className={`ws-status ws-status--${wsState}`}
          title={wsLabel}
        >
          {wsState === "connected" ? (
            <Wifi size={20} strokeWidth={1.75} aria-hidden="true" />
          ) : (
            <WifiOff size={20} strokeWidth={1.75} aria-hidden="true" />
          )}
          <span>{wsLabel}</span>
        </span>
      </div>
    </header>
  );
}