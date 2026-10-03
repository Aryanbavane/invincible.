import { AlertTriangle, ArrowRight, CheckCircle2, CircleHelp } from "lucide-react";
import type {
  ChartPoint,
  CommandEvent,
  DeviceStatus,
  SensorSnapshot,
  TodayStats,
  TimelineEntry,
} from "../types";
import CommandGlyph from "../components/CommandGlyph";
import ConfidenceBar from "../components/ConfidenceBar";
import EmergencyDialog from "../components/EmergencyDialog";
import EventTimeline from "../components/EventTimeline";
import EyeIllustration from "../components/EyeIllustration";
import EmgChart from "../charts/EmgChart";
import IrChart from "../charts/IrChart";
import type { EmergencyState } from "../types";

interface LiveDashboardProps {
  sensor: SensorSnapshot | null;
  chartData: ChartPoint[];
  latestCommand: CommandEvent | null;
  timeline: TimelineEntry[];
  stats: TodayStats;
  pattern: Array<"SHORT" | "LONG">;
  patternFinalized: boolean;
  lastBlinkDuration: number | null;
  deviceStatus: DeviceStatus | null;
  mode: "live" | "demo";
  feedback: string | null;
  emergencyPending: boolean;
  emergency: EmergencyState | null;
  onAcknowledgeEmergency: () => void;
  onCloseEmergency: () => void;
  onHistory: () => void;
  apiError: string | null;
}

function percent(value: number | undefined) {
  return `${Math.round(value ?? 0)}%`;
}

function confidenceText(value: number) {
  if (value >= 85) return "Intent confirmed";
  if (value >= 70) return "Possible intent";
  return "Signal uncertain, please repeat";
}

function timeText(timestamp?: string) {
  if (!timestamp) return "—";
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function LiveDashboard({
  sensor,
  chartData,
  latestCommand,
  timeline,
  stats,
  pattern,
  patternFinalized,
  lastBlinkDuration,
  deviceStatus,
  mode,
  feedback,
  emergencyPending,
  emergency,
  onAcknowledgeEmergency,
  onCloseEmergency,
  onHistory,
  apiError,
}: LiveDashboardProps) {
  const fusion = sensor?.fusion.fusion_confidence ?? 0;
  const isConfirmed = fusion >= 85 && sensor?.fusion.intent_confirmed;
  const isPossible = fusion >= 70 && fusion < 85;
  const activityDetected =
    sensor?.emg.threshold !== null &&
    sensor?.emg.threshold !== undefined &&
    sensor.emg.activity > sensor.emg.threshold;
  const freshness =
    mode === "demo"
      ? "SIMULATED"
      : sensor
        ? "Receiving"
        : "Awaiting sensor data";
  const deviceOffline = mode === "live" && deviceStatus?.status !== "ONLINE";

  return (
    <>
      <main className="dashboard-content" id="live">
        {deviceOffline && (
          <div className="notice notice--warn" role="status">
            <AlertTriangle size={20} strokeWidth={1.75} aria-hidden="true" />
            <span>Device offline. Waiting for an ESP32 heartbeat.</span>
          </div>
        )}
        {apiError && (
          <div className="notice notice--warn" role="status">
            <AlertTriangle size={20} strokeWidth={1.75} aria-hidden="true" />
            <span>{apiError}</span>
          </div>
        )}

        <section className="story-strip" aria-label="How a blink becomes a message">
          <div className="story-zone story-zone--sense">
            <div className="zone-heading">
              <span className="zone-number">01</span>
              <div>
                <p className="eyebrow">SENSE</p>
                <h2>Two signals, one gesture</h2>
              </div>
            </div>
            <div className="sensor-rows">
              <div className="sensor-row sensor-row--ir">
                <div className="sensor-row-heading">
                  <span className="sensor-name">IR eye sensor</span>
                  <span className="sensor-freshness">{freshness}</span>
                </div>
                <div className="sensor-row-detail">
                  <span>Eye {sensor?.ir.state.toLowerCase() ?? "open"}</span>
                  <span className="mono-number">{percent(sensor?.ir.confidence)}</span>
                </div>
                <ConfidenceBar
                  label="IR confidence"
                  value={sensor?.ir.confidence ?? 0}
                  kind="ir"
                />
              </div>
              <div className="sensor-row sensor-row--emg">
                <div className="sensor-row-heading">
                  <span className="sensor-name">EMG Muscle Sensor V3.0</span>
                  {sensor?.source === "demo" && <span className="source-tag">SIMULATED</span>}
                </div>
                <div className="sensor-row-detail">
                  <span>Activity {Math.round(sensor?.emg.activity ?? 0)}%</span>
                  <span>Baseline {sensor?.emg.baseline ?? "—"}</span>
                  <span className="mono-number">{percent(sensor?.emg.confidence)}</span>
                </div>
                <ConfidenceBar
                  label="EMG confidence"
                  value={sensor?.emg.confidence ?? 0}
                  kind="emg"
                />
              </div>
            </div>
          </div>

          <div className="story-connector" aria-hidden="true">
            <ArrowRight size={20} strokeWidth={1.75} />
          </div>

          <div className="story-zone story-zone--understand">
            <div className="zone-heading">
              <span className="zone-number">02</span>
              <div>
                <p className="eyebrow">UNDERSTAND</p>
                <h2>Dual-sensor fusion</h2>
              </div>
            </div>
            <div className="fusion-inputs">
              <span><i className="legend-dot legend-dot--ir" />IR {percent(sensor?.fusion.ir_confidence)}</span>
              <span className="mono-number">+</span>
              <span><i className="legend-dot legend-dot--emg" />EMG {percent(sensor?.fusion.emg_confidence)}</span>
            </div>
            <div
              aria-label={`Fusion confidence ${Math.round(fusion)} percent`}
              className={`fusion-meter ${isConfirmed ? "fusion-meter--confirmed" : ""}`}
              role="meter"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(fusion)}
            >
              <div className="fusion-meter-track">
                <span className="fusion-meter-fill" style={{ width: `${fusion}%` }} />
                <i className="fusion-tick fusion-tick--possible" />
                <i className="fusion-tick fusion-tick--confirmed" />
              </div>
              <div className="fusion-tick-labels mono-number"><span>70</span><span>85</span></div>
            </div>
            <div className="fusion-result" aria-live="polite">
              {isConfirmed ? (
                <CheckCircle2 size={20} strokeWidth={1.75} aria-hidden="true" />
              ) : isPossible || emergencyPending ? (
                <CircleHelp size={20} strokeWidth={1.75} aria-hidden="true" />
              ) : (
                <AlertTriangle size={20} strokeWidth={1.75} aria-hidden="true" />
              )}
              <span>{feedback ?? (emergencyPending ? "Second long blink needed" : sensor ? confidenceText(fusion) : "Waiting for a gesture")}</span>
              <strong className="fusion-number mono-number">{Math.round(fusion)}</strong>
            </div>
          </div>

          <div className="story-connector" aria-hidden="true">
            <ArrowRight size={20} strokeWidth={1.75} />
          </div>

          <div className="story-zone story-zone--communicate">
            <div className="zone-heading">
              <span className="zone-number">03</span>
              <div>
                <p className="eyebrow">COMMUNICATE</p>
                <h2>Message</h2>
              </div>
            </div>
            <div className="command-output" aria-live="polite">
              {latestCommand ? (
                <>
                  <CommandGlyph command={latestCommand.command} />
                  <p className="hero-message">{latestCommand.message}</p>
                  <p className="speaker-line">
                    Speaker: {latestCommand.audio_id}.mp3 · {latestCommand.source === "demo" ? "SIMULATED" : "awaiting hardware"}
                  </p>
                  <time className="command-time mono-number" dateTime={latestCommand.timestamp}>
                    {timeText(latestCommand.timestamp)}
                  </time>
                  {latestCommand.source === "demo" && <span className="source-tag">DEMO EVENT</span>}
                </>
              ) : (
                <div className="idle-message">
                  <CommandGlyph />
                  <p className="hero-message">Waiting for a gesture</p>
                  <p className="speaker-line">No message detected</p>
                </div>
              )}
            </div>
          </div>
        </section>

        <div className="dashboard-row dashboard-row--two">
          <section className="panel gesture-panel" aria-labelledby="gesture-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">GESTURE</p>
                <h2 id="gesture-title">Blink and pattern</h2>
              </div>
              {sensor?.source === "demo" && <span className="source-tag">SIMULATED</span>}
            </div>
            <div className="gesture-content">
              <div className="eye-wrap">
                <EyeIllustration blink={sensor?.ir.state === "CLOSED"} />
                <div className="eye-status-line">
                  <span className={`eye-state-dot ${sensor?.ir.state === "CLOSED" ? "eye-state-dot--closed" : ""}`} />
                  <span>{sensor?.ir.state === "CLOSED" ? "Eye closed" : "Eye open"}</span>
                </div>
                <p className="duration-readout mono-number">
                  {lastBlinkDuration === null ? "— ms" : `${lastBlinkDuration} ms`}
                </p>
              </div>
              <div className="pattern-readout">
                <span className="eyebrow">{patternFinalized ? "LAST PATTERN" : "PATTERN IN PROGRESS"}</span>
                <div className="pattern-symbols" aria-label={pattern.length ? `${pattern.length} confirmed blinks` : "No blinks in progress"}>
                  {pattern.length ? pattern.map((kind, index) => (
                    <span
                      className={kind === "SHORT" ? "pattern-dot" : "pattern-pill"}
                      key={`${kind}-${index}`}
                    />
                  )) : <span className="pattern-empty-mark" />}
                </div>
                <p className="pattern-caption">
                  {pattern.length
                    ? `${pattern.length} ${pattern[0]?.toLowerCase()} ${pattern.length === 1 ? "blink" : "blinks"}`
                    : "Waiting for a gesture"}
                </p>
                <div className={`pattern-gap ${pattern.length && !patternFinalized ? "pattern-gap--active" : ""}`} aria-hidden="true">
                  <span key={pattern.length} />
                </div>
                <span className="pattern-gap-caption">Pattern gap · 1.5 s</span>
              </div>
            </div>
          </section>

          <section className="panel chart-panel" aria-labelledby="ir-chart-title">
            <div className="panel-heading panel-heading--chart">
              <div>
                <p className="eyebrow eyebrow--ir">IR SENSOR · BLUE</p>
                <h2 id="ir-chart-title">Eye state</h2>
              </div>
              <span className="chart-legend"><i className="legend-dot legend-dot--ir" />Open / closed</span>
            </div>
            <IrChart data={chartData} />
          </section>
        </div>

        <div className="dashboard-row dashboard-row--three">
          <section className="panel chart-panel" aria-labelledby="emg-chart-title">
            <div className="panel-heading panel-heading--chart">
              <div>
                <p className="eyebrow eyebrow--emg">EMG SENSOR · AMBER</p>
                <h2 id="emg-chart-title">Muscle activity</h2>
              </div>
              {activityDetected && <span className="activity-status"><CheckCircle2 size={20} strokeWidth={1.75} />Activity detected</span>}
            </div>
            <EmgChart data={chartData} activityDetected={activityDetected} />
          </section>

          <section className="panel timeline-panel" aria-labelledby="timeline-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">RECENT</p>
                <h2 id="timeline-title">Event timeline</h2>
              </div>
              <span className="timeline-count mono-number">{timeline.length.toString().padStart(2, "0")} / 12</span>
            </div>
            <EventTimeline entries={timeline} />
          </section>
        </div>

        <section className="today-line" aria-label="Today's communication totals">
          <strong>Today</strong>
          <span>Yes <b>{stats.by_command.YES ?? 0}</b></span>
          <i aria-hidden="true">·</i>
          <span>No <b>{stats.by_command.NO ?? 0}</b></span>
          <i aria-hidden="true">·</i>
          <span>Water <b>{stats.by_command.WATER ?? 0}</b></span>
          <i aria-hidden="true">·</i>
          <span>Pain <b>{stats.by_command.PAIN ?? 0}</b></span>
          <i aria-hidden="true">·</i>
          <span>Help <b>{stats.by_command.HELP ?? 0}</b></span>
          <button className="text-link" onClick={onHistory} type="button">View history <span aria-hidden="true">→</span></button>
        </section>

        <section className="how-section" aria-labelledby="how-title">
          <div className="how-heading">
            <p className="eyebrow">A CLEAR SIGNAL PATH</p>
            <h2 id="how-title">How BlinkBridge understands you</h2>
          </div>
          <ol className="how-steps">
            <li><span className="how-number">01</span><p>The IR sensor notices an eye-state change.</p></li>
            <li><span className="how-number">02</span><p>EMG activity must agree before a blink is confirmed.</p></li>
            <li><span className="how-number">03</span><p>A confirmed pattern resolves to a spoken-message file.</p></li>
          </ol>
          <p className="prototype-note">Prototype signal rules only. Not medical-grade or certified.</p>
        </section>
      </main>

      {emergency && (
        <EmergencyDialog
          emergency={emergency}
          onAcknowledge={onAcknowledgeEmergency}
          onClose={onCloseEmergency}
        />
      )}
    </>
  );
}