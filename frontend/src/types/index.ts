export type Language = "en" | "hi" | "mr";
export type AppPage = "Live" | "Calibration" | "History" | "Device" | "Settings";
export type DemoScenario =
  | "YES"
  | "NO"
  | "HELP"
  | "WATER"
  | "PAIN"
  | "COME_HERE"
  | "LOW_CONFIDENCE"
  | "SENSOR_NOISE"
  | "EMERGENCY"
  | "DEVICE_OFFLINE";

export interface CommandEvent {
  device_id: string;
  pattern: string;
  command: string;
  message: string;
  ir_confidence: number;
  emg_confidence: number;
  fusion_confidence: number;
  audio_id: string;
  timestamp: string;
  source: "live" | "demo";
}

export interface SensorSnapshot {
  device_id: string;
  timestamp: string;
  source: "live" | "demo";
  emg: {
    raw: number;
    filtered: number;
    baseline: number | null;
    activity: number;
    threshold: number | null;
    confidence: number;
  };
  ir: {
    state: "OPEN" | "CLOSED";
    duration_ms: number;
    confidence: number;
  };
  fusion: {
    ir_confidence: number;
    emg_confidence: number;
    fusion_confidence: number;
    intent_confirmed: boolean;
  };
  fusion_level: "intent_confirmed" | "possible_intent" | "low";
}

export interface HistoryEvent {
  event_id?: number;
  emergency_id?: number;
  event_type: "communication" | "emergency";
  device_id: string;
  command?: string;
  message: string;
  pattern?: string;
  timestamp: string;
  source: "live" | "demo";
  acknowledged?: number;
  audio_id?: string;
}

export interface TimelineEntry {
  id: string;
  timestamp: string;
  sentence: string;
  source: "live" | "demo";
  kind: "communication" | "emergency" | "sensor";
}

export interface ChartPoint {
  timestamp: number;
  label: string;
  eye: number;
  signal: number;
  activity: number;
  baseline: number;
  threshold: number;
}

export interface DeviceStatus {
  device_id: string;
  status: "ONLINE" | "OFFLINE";
  last_seen: string | null;
  battery: number | null;
  age_seconds: number | null;
  source?: "demo" | "live";
}

export interface TodayStats {
  date: string;
  total: number;
  by_command: Record<string, number>;
  emergency_total: number;
}

export interface EmergencyState {
  emergency_id: number;
  message: string;
  audio_id?: string;
  acknowledged: boolean;
  source: "live" | "demo";
}

export interface DemoResponse {
  scenario: DemoScenario;
  source: "demo";
  events_processed: number;
  command: CommandEvent | null;
  audio_id: string | null;
  emergency_id: number | null;
  device_status?: DeviceStatus;
  results?: Array<Record<string, unknown>>;
}

export interface DashboardMessage {
  type: string;
  payload?: unknown;
}