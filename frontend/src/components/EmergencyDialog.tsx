import { AlertTriangle, Check, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { EmergencyState } from "../types";

interface EmergencyDialogProps {
  emergency: EmergencyState;
  onAcknowledge: () => void;
  onClose: () => void;
}

export default function EmergencyDialog({
  emergency,
  onAcknowledge,
  onClose,
}: EmergencyDialogProps) {
  const actionRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    actionRef.current?.focus();
  }, []);

  return (
    <div className="emergency-backdrop">
      <section
        aria-labelledby="emergency-title"
        aria-modal="true"
        className="emergency-dialog"
        role="alertdialog"
      >
        <div className="emergency-dialog-heading">
          <AlertTriangle size={20} strokeWidth={1.75} aria-hidden="true" />
          <div>
            <p className="eyebrow">LOCAL CAREGIVER ALERT</p>
            <h2 id="emergency-title">
              {emergency.acknowledged ? "Emergency acknowledged" : "Emergency confirmed"}
            </h2>
          </div>
          {emergency.acknowledged && (
            <button className="icon-button emergency-close" onClick={onClose} aria-label="Close alert" type="button">
              <X size={20} strokeWidth={1.75} />
            </button>
          )}
        </div>
        <p className="emergency-message">{emergency.message}</p>
        <div className="emergency-meta mono-number">
          <span>Audio: {emergency.audio_id ?? "0007"}.mp3</span>
          <span>{emergency.source === "demo" ? "SIMULATED" : "LOCAL ALERT"}</span>
        </div>
        {emergency.acknowledged ? (
          <button className="button button--primary emergency-action" onClick={onClose} type="button">
            <Check size={20} strokeWidth={1.75} />
            Done
          </button>
        ) : (
          <button
            className="button button--danger emergency-action"
            onClick={onAcknowledge}
            ref={actionRef}
            type="button"
          >
            <Check size={20} strokeWidth={1.75} />
            Acknowledge
          </button>
        )}
      </section>
    </div>
  );
}