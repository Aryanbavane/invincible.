import {
  Activity,
  CircleHelp,
  Droplet,
  HeartPulse,
  Radio,
  Siren,
  UserRound,
  WifiOff,
  X,
  Check,
} from "lucide-react";
import type { ComponentType } from "react";
import type { DemoScenario } from "../types";

const scenarios: Array<{
  id: DemoScenario;
  label: string;
  Icon: ComponentType<{ size?: number; strokeWidth?: number }>;
}> = [
  { id: "YES", label: "YES", Icon: Check },
  { id: "NO", label: "NO", Icon: X },
  { id: "HELP", label: "HELP", Icon: CircleHelp },
  { id: "WATER", label: "WATER", Icon: Droplet },
  { id: "PAIN", label: "PAIN", Icon: HeartPulse },
  { id: "COME_HERE", label: "COME HERE", Icon: UserRound },
  { id: "LOW_CONFIDENCE", label: "LOW CONFIDENCE", Icon: Activity },
  { id: "SENSOR_NOISE", label: "SENSOR NOISE", Icon: Radio },
  { id: "EMERGENCY", label: "EMERGENCY", Icon: Siren },
  { id: "DEVICE_OFFLINE", label: "DEVICE OFFLINE", Icon: WifiOff },
];

interface DemoControlsProps {
  active: DemoScenario | null;
  onSimulate: (scenario: DemoScenario) => void;
  onClose?: () => void;
}

export default function DemoControls({
  active,
  onSimulate,
  onClose,
}: DemoControlsProps) {
  return (
    <section className="demo-controls" aria-labelledby="demo-controls-title">
      <div className="demo-controls-heading">
        <div>
          <h2 id="demo-controls-title">Demo controls</h2>
          <span>SIMULATED SENSOR INPUT</span>
        </div>
        {onClose && (
          <button
            aria-label="Close demo controls"
            className="icon-button mobile-demo-close"
            onClick={onClose}
            type="button"
          >
            <X size={20} strokeWidth={1.75} />
          </button>
        )}
      </div>
      <div className="demo-grid">
        {scenarios.map(({ id, label, Icon }) => (
          <button
            aria-pressed={active === id}
            className={`demo-button ${id === "EMERGENCY" ? "demo-button--emergency" : ""}`}
            disabled={active !== null}
            key={id}
            onClick={() => onSimulate(id)}
            type="button"
          >
            <Icon aria-hidden="true" size={20} strokeWidth={1.75} />
            <span>{active === id ? "Running…" : `Simulate ${label}`}</span>
          </button>
        ))}
      </div>
    </section>
  );
}