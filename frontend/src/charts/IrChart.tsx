import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint } from "../types";

export default function IrChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="chart-frame">
      {data.length === 0 && <span className="chart-empty">Waiting for sensor samples</span>}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 12, right: 12, bottom: 2, left: -14 }}>
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
            domain={[0, 1]}
            ticks={[0, 1]}
            tickFormatter={(value: number) => (value === 1 ? "Closed" : "Open")}
            tick={{ fill: "var(--muted)", fontSize: 14 }}
            tickLine={false}
            axisLine={false}
            width={58}
          />
          <Tooltip
            labelFormatter={(value) => new Date(Number(value)).toLocaleTimeString()}
            formatter={(value) => [Number(value) === 1 ? "Closed" : "Open", "IR eye"]}
            contentStyle={{ border: "1px solid var(--line)", borderRadius: 8, fontSize: 14 }}
          />
          <Line
            dataKey="eye"
            name="IR eye state"
            type="stepAfter"
            stroke="var(--ir)"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}