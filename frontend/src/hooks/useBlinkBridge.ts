import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type {
  AppPage,
  ChartPoint,
  CommandEvent,
  DemoScenario,
  DeviceStatus,
  EmergencyState,
  HistoryEvent,
  Language,
  SensorSnapshot,
  TodayStats,
  TimelineEntry,
} from "../types";

function timelineFromHistory(events: HistoryEvent[]): TimelineEntry[] {
  return events.slice(0, 12).map((event) => ({
    id: `${event.event_type}-${event.event_id ?? event.emergency_id}`,
    timestamp: event.timestamp,
    sentence:
      event.event_type === "emergency"
        ? event.acknowledged
          ? "Emergency acknowledged"
          : "Emergency confirmed"
        : `Said “${event.message}”`,
    source: event.source,
    kind: event.event_type,
  }));
}

function timelineFromCommand(event: CommandEvent): TimelineEntry {
  return {
    id: `command-${event.timestamp}-${event.command}`,
    timestamp: event.timestamp,
    sentence: `Said “${event.message}”`,
    source: event.source,
    kind: "communication",
  };
}

export function useBlinkBridge() {
  const [page, setPage] = useState<AppPage>("Live");
  const [language, setLanguage] = useState<Language>("en");
  const [wsState, setWsState] = useState<"connecting" | "connected" | "reconnecting">(
    "connecting",
  );
  const [apiOnline, setApiOnline] = useState(false);
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatus | null>(null);
  const [sensor, setSensor] = useState<SensorSnapshot | null>(null);
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [latestCommand, setLatestCommand] = useState<CommandEvent | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [stats, setStats] = useState<TodayStats>({
    date: new Date().toISOString().slice(0, 10),
    total: 0,
    by_command: {},
    emergency_total: 0,
  });
  const [pattern, setPattern] = useState<Array<"SHORT" | "LONG">>([]);
  const [patternFinalized, setPatternFinalized] = useState(false);
  const [lastBlinkDuration, setLastBlinkDuration] = useState<number | null>(null);
  const [emergency, setEmergency] = useState<EmergencyState | null>(null);
  const [emergencyPending, setEmergencyPending] = useState(false);
  const [simulating, setSimulating] = useState<DemoScenario | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const patternTimer = useRef<number | null>(null);
  const patternFinalizedRef = useRef(false);

  async function refreshHistory() {
    const [historyResult, statsResult] = await Promise.all([
      api.history(),
      api.todayStats(),
    ]);
    setTimeline(timelineFromHistory(historyResult.events));
    setStats(statsResult);
  }

  useEffect(() => {
    let disposed = false;
    async function loadInitialState() {
      try {
        const [health, historyResult, statsResult, settings, status] =
          await Promise.all([
            api.health(),
            api.history(),
            api.todayStats(),
            api.settings(),
            api.deviceStatus(),
          ]);
        if (disposed) return;
        setApiOnline(health.status === "ok");
        setTimeline(timelineFromHistory(historyResult.events));
        setStats(statsResult);
        setMode(settings.mode);
        const availableDevices = Array.isArray(status) ? status : [status];
        setDeviceStatus(availableDevices[0] ?? null);
        setApiError(null);
      } catch (error) {
        if (!disposed) {
          setApiOnline(false);
          setApiError(
            error instanceof Error ? error.message : "Backend is unavailable",
          );
        }
      }
    }
    void loadInitialState();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let attempts = 0;

    function connect() {
      if (disposed) return;
      setWsState(attempts === 0 ? "connecting" : "reconnecting");
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard`);
      socket.onopen = () => {
        attempts = 0;
        setWsState("connected");
      };
      socket.onmessage = (message) => {
        try {
          const update = JSON.parse(message.data) as {
            type: string;
            payload?: Record<string, unknown>;
            device_id?: string;
            blink_type?: "SHORT" | "LONG";
            duration_ms?: number;
          };
          if (update.type === "SENSOR_UPDATE" && update.payload) {
            const snapshot = update.payload as unknown as SensorSnapshot;
            setSensor(snapshot);
            setFeedback(
              snapshot.fusion_level === "low"
                ? "Signal uncertain, please repeat"
                : snapshot.fusion_level === "possible_intent"
                  ? "Possible intent"
                  : null,
            );
            setChartData((points) => {
              const next: ChartPoint = {
                timestamp: Date.parse(snapshot.timestamp),
                label: new Date(snapshot.timestamp).toLocaleTimeString([], {
                  minute: "2-digit",
                  second: "2-digit",
                }),
                eye: snapshot.ir.state === "CLOSED" ? 1 : 0,
                signal: snapshot.emg.filtered,
                activity: snapshot.emg.activity,
                baseline: snapshot.emg.baseline ?? 0,
                threshold:
                  (snapshot.emg.baseline ?? 0) + (snapshot.emg.threshold ?? 0),
              };
              return [...points, next].slice(-80);
            });
          } else if (update.type === "BLINK_DETECTED" && update.blink_type) {
            setLastBlinkDuration(update.duration_ms ?? null);
            const replacePattern = patternFinalizedRef.current;
            patternFinalizedRef.current = false;
            setPatternFinalized(false);
            setPattern((current) =>
              (replacePattern ? [update.blink_type!] : [...current, update.blink_type!]).slice(-5),
            );
            if (patternTimer.current !== null) {
              window.clearTimeout(patternTimer.current);
            }
            patternTimer.current = window.setTimeout(() => setPattern([]), 1500);
          } else if (update.type === "COMMAND_DETECTED" && update.payload) {
            const command = update.payload as unknown as CommandEvent;
            setLatestCommand(command);
            const completedPattern = command.pattern
              .split("_")
              .filter((item): item is "SHORT" | "LONG" => item === "SHORT" || item === "LONG");
            if (completedPattern.length) {
              patternFinalizedRef.current = true;
              setPatternFinalized(true);
              setPattern(completedPattern.slice(-5));
              if (patternTimer.current !== null) {
                window.clearTimeout(patternTimer.current);
                patternTimer.current = null;
              }
            }
            setFeedback(null);
            setTimeline((current) =>
              [timelineFromCommand(command), ...current]
                .filter(
                  (entry, index, entries) =>
                    entries.findIndex((candidate) => candidate.id === entry.id) ===
                    index,
                )
                .slice(0, 12),
            );
            void refreshHistory().catch(() => undefined);
          } else if (update.type === "EMERGENCY_PENDING") {
            setEmergencyPending(true);
          } else if (update.type === "EMERGENCY_CONFIRMED" && update.payload) {
            const payload = update.payload;
            const command = payload.command as CommandEvent | undefined;
            const emergencyPattern = command?.pattern
              .split("_")
              .filter((item): item is "SHORT" | "LONG" => item === "SHORT" || item === "LONG");
            if (emergencyPattern?.length) {
              patternFinalizedRef.current = true;
              setPatternFinalized(true);
              setPattern(emergencyPattern.slice(-5));
              if (patternTimer.current !== null) {
                window.clearTimeout(patternTimer.current);
                patternTimer.current = null;
              }
            }
            if (typeof payload.emergency_id === "number") {
              setEmergency({
                emergency_id: payload.emergency_id,
                message: command?.message ?? "Emergency. Please help me",
                audio_id: command?.audio_id,
                acknowledged: payload.acknowledged === 1,
                source: command?.source ?? (payload.source === "demo" ? "demo" : "live"),
              });
            }
            setEmergencyPending(false);
            void refreshHistory().catch(() => undefined);
          } else if (update.type === "DEVICE_STATUS" && update.payload) {
            const payload = update.payload;
            if (payload.mode === "demo" || payload.mode === "live") {
              setMode(payload.mode);
            }
            if (typeof payload.device_id === "string") {
              setDeviceStatus(payload as unknown as DeviceStatus);
            }
          }
        } catch {
          setApiError("A dashboard update could not be read");
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (disposed) return;
        setWsState("reconnecting");
        attempts += 1;
        reconnectTimer = window.setTimeout(
          connect,
          Math.min(1000 * 2 ** Math.min(attempts - 1, 3), 8000),
        );
      };
    }

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (patternTimer.current !== null) window.clearTimeout(patternTimer.current);
      socket?.close();
    };
  }, []);

  async function simulate(scenario: DemoScenario) {
    setSimulating(scenario);
    setMode("demo");
    setApiError(null);
    if (scenario === "LOW_CONFIDENCE" || scenario === "SENSOR_NOISE") {
      setLatestCommand(null);
      setLastBlinkDuration(null);
      patternFinalizedRef.current = false;
      setPatternFinalized(false);
      setPattern([]);
      if (patternTimer.current !== null) {
        window.clearTimeout(patternTimer.current);
        patternTimer.current = null;
      }
    }
    try {
      const result = await api.simulate(scenario, language);
      if (result.command) {
        setLatestCommand(result.command);
        const completedPattern = result.command.pattern
          .split("_")
          .filter((item): item is "SHORT" | "LONG" => item === "SHORT" || item === "LONG");
        if (completedPattern.length) {
          patternFinalizedRef.current = true;
          setPatternFinalized(true);
          setPattern(completedPattern.slice(-5));
          if (patternTimer.current !== null) {
            window.clearTimeout(patternTimer.current);
            patternTimer.current = null;
          }
        }
      }
      if (result.emergency_id !== null) {
        setEmergency({
          emergency_id: result.emergency_id,
          message: result.command?.message ?? "Emergency. Please help me",
          audio_id: result.audio_id ?? undefined,
          acknowledged: false,
          source: "demo",
        });
      }
      if (scenario === "DEVICE_OFFLINE" && result.device_status) {
        setDeviceStatus(result.device_status as unknown as DeviceStatus);
      }
      if (!result.command && (scenario === "LOW_CONFIDENCE" || scenario === "SENSOR_NOISE")) {
        setFeedback("Signal uncertain, please repeat");
      }
      await refreshHistory();
      return result;
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Simulation failed");
      return null;
    } finally {
      setSimulating(null);
    }
  }

  async function acknowledgeEmergency() {
    if (!emergency) return;
    try {
      await api.acknowledge(emergency.emergency_id);
      setEmergency({ ...emergency, acknowledged: true });
      await refreshHistory();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Acknowledgement failed");
    }
  }

  function dismissEmergency() {
    if (emergency?.acknowledged) setEmergency(null);
  }

  return {
    page,
    setPage,
    language,
    setLanguage,
    wsState,
    apiOnline,
    mode,
    deviceStatus,
    sensor,
    chartData,
    latestCommand,
    timeline,
    stats,
    pattern,
    patternFinalized,
    lastBlinkDuration,
    emergency,
    emergencyPending,
    simulating,
    feedback,
    apiError,
    simulate,
    acknowledgeEmergency,
    dismissEmergency,
  };
}