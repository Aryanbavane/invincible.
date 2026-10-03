import { AlertTriangle, MessageSquareText } from "lucide-react";
import type { TimelineEntry } from "../types";

interface EventTimelineProps {
  entries: TimelineEntry[];
}

function displayTime(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function EventTimeline({ entries }: EventTimelineProps) {
  return (
    <ol className="event-timeline" aria-label="Recent events">
      {entries.length === 0 ? (
        <li className="timeline-empty">No messages yet</li>
      ) : (
        entries.slice(0, 12).map((entry) => (
          <li className="timeline-row" key={entry.id}>
            <time className="timeline-time mono-number" dateTime={entry.timestamp}>
              {displayTime(entry.timestamp)}
            </time>
            {entry.kind === "emergency" ? (
              <AlertTriangle className="timeline-icon timeline-icon--emergency" size={20} strokeWidth={1.75} />
            ) : (
              <MessageSquareText className="timeline-icon" size={20} strokeWidth={1.75} />
            )}
            <span className="timeline-sentence">{entry.sentence}</span>
            {entry.source === "demo" && <span className="source-tag">SIMULATED</span>}
          </li>
        ))
      )}
    </ol>
  );
}