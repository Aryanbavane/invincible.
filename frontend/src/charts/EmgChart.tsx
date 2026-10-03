import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint } from "../types";

interface EmgChartProps {
  data: ChartPoint[];
  activityDetected: boolean;
}

export default function EmgChart({ data, activityDetected }: EmgChartProps) {
  return (
    <div className="chart-frame">
      {activityDetected && <span className="activity-label">Activity detected</span>}
      {data.length === 0 && <span className="chart-empty">Waiting for sensor samples</span>}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 12, right: 12, bottom: 2, left: -14 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value: number) =>
              new Date(value).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" })
            }
            tick={{ fill: "var(--muted)", fontSize: 14, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--line)" }}
            minTickGap={32}
          />
          <YAxis
            tick={{ fill: "var(--muted)", fontSize: 14, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
            width={52}
          />
          <Tooltip
            labelFormatter={(value) => new Date(Number(value)).toLocaleTimeString()}
            formatter={(value, name) => [Number(value).toFixed(1), name]}
            contentStyle={{ border: "1px solid var(--line)", borderRadius: 8, fontSize: 14 }}
          />
          <Area
            dataKey="signal"
            name="Filtered EMG"
            type="monotone"
            stroke="var(--emg)"
            strokeWidth={2.5}
            fill="var(--emg)"
            fillOpacity={0.1}
            isAnimationActive={false}
          />
          <Line
            dataKey="baseline"
            name="Baseline"
            type="monotone"
            stroke="var(--muted)"
            strokeDasharray="5 5"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="threshold"
            name="Threshold"
            type="monotone"
            stroke="var(--fusion)"
            strokeDasharray="5 5"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}