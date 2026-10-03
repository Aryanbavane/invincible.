import type {
  CommandEvent,
  DemoResponse,
  DemoScenario,
  DeviceStatus,
  HistoryEvent,
  TodayStats,
} from "../types";

interface HistoryResponse {
  events: HistoryEvent[];
  count: number;
}

interface SettingsResponse {
  mode: "live" | "demo";
  device_offline_timeout_seconds: number;
  supported_sensor_mode: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item: { msg?: string }) => item.msg).join("; ")
      : body?.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  history: () => request<HistoryResponse>("/api/history?limit=100"),
  todayStats: () => request<TodayStats>("/api/stats/today"),
  deviceStatus: () =>
    request<DeviceStatus[] | DeviceStatus>("/api/device/status"),
  settings: () => request<SettingsResponse>("/api/settings"),
  simulate: (scenario: DemoScenario, language: string) =>
    request<DemoResponse>("/api/demo/simulate", {
      method: "POST",
      body: JSON.stringify({ scenario, language }),
    }),
  acknowledge: (emergencyId: number) =>
    request<Record<string, unknown>>(
      `/api/emergency/${emergencyId}/acknowledge`,
      { method: "POST" },
    ),
  manualEmergency: (deviceId: string) =>
    request<{
      state: string;
      emergency_id: number;
      command: CommandEvent;
    }>("/api/emergency", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId }),
    }),
};

export type { HistoryResponse, SettingsResponse };