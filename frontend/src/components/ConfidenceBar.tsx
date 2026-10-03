interface ConfidenceBarProps {
  label: string;
  value: number;
  kind: "ir" | "emg";
}

export default function ConfidenceBar({ label, value, kind }: ConfidenceBarProps) {
  const bounded = Math.min(100, Math.max(0, value));
  return (
    <div className={`confidence-bar confidence-bar--${kind}`}>
      <div className="confidence-bar-label">
        <span>{label}</span>
        <span className="mono-number">{Math.round(bounded)}%</span>
      </div>
      <div
        aria-label={`${label} confidence ${Math.round(bounded)} percent`}
        className="confidence-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(bounded)}
      >
        <span style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}