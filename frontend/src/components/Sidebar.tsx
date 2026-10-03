import {
  Activity,
  Cpu,
  History,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import type { ComponentType } from "react";
import type { AppPage, DemoScenario } from "../types";
import DemoControls from "./DemoControls";

const navigation: Array<{
  name: AppPage;
  Icon: ComponentType<{ size?: number; strokeWidth?: number }>;
}> = [
  { name: "Live", Icon: Activity },
  { name: "Calibration", Icon: SlidersHorizontal },
  { name: "History", Icon: History },
  { name: "Device", Icon: Cpu },
  { name: "Settings", Icon: Settings },
];

interface SidebarProps {
  page: AppPage;
  onNavigate: (page: AppPage) => void;
  onSimulate: (scenario: DemoScenario) => void;
  simulating: DemoScenario | null;
}

export default function Sidebar({
  page,
  onNavigate,
  onSimulate,
  simulating,
}: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <a className="brand" href="#live" onClick={() => onNavigate("Live")}>
        <svg
          aria-hidden="true"
          className="brand-mark"
          fill="none"
          viewBox="0 0 38 38"
        >
          <path d="M4 19c4.5-7 10-10.5 15-10.5S29.5 12 34 19c-4.5 7-10 10.5-15 10.5S8.5 26 4 19Z" />
          <path d="M12.5 19c2-3 4.2-4.5 6.5-4.5s4.5 1.5 6.5 4.5c-2 3-4.2 4.5-6.5 4.5s-4.5-1.5-6.5-4.5Z" />
          <circle cx="19" cy="19" r="2.2" />
        </svg>
        <span>BlinkBridge</span>
      </a>

      <nav className="primary-nav">
        <span className="nav-caption">WORKSPACE</span>
        {navigation.map(({ name, Icon }) => (
          <button
            aria-current={page === name ? "page" : undefined}
            className={`nav-item ${page === name ? "nav-item--active" : ""}`}
            key={name}
            onClick={() => onNavigate(name)}
            type="button"
          >
            <Icon aria-hidden="true" size={20} strokeWidth={1.75} />
            <span>{name}</span>
            {name !== "Live" && <span className="nav-soon">NOT BUILT</span>}
          </button>
        ))}
      </nav>

      <DemoControls active={simulating} onSimulate={onSimulate} />
    </aside>
  );
}