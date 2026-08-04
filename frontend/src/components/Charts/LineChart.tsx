import React from "react";
import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface LineChartProps {
  data: Record<string, any>[];
  xAxisKey: string;
  dataKeys: string[];
}

const VIBRANT_LINE_COLORS = [
  "#06B6D4", // Bright Cyan
  "#F97316", // Vibrant Orange
  "#10B981", // Emerald Green
  "#8B5CF6", // Vivid Purple
  "#F59E0B", // Amber Gold
  "#EC4899", // Bright Pink
  "#3B82F6", // Royal Blue
  "#84CC16", // Bright Lime
  "#E11D48", // Crimson Rose
  "#6366F1", // Indigo
];

export const LineChart: React.FC<LineChartProps> = ({ data, xAxisKey, dataKeys }) => {
  const keys = dataKeys && dataKeys.length > 0 ? dataKeys : ["value"];

  return (
    <div className="h-64 w-full bg-surface-2/80 border border-border rounded-xl p-3 shadow-xs font-sans">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart
          data={data}
          margin={{
            top: 10,
            right: 15,
            left: -15,
            bottom: keys.length > 1 ? 25 : 10,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" vertical={false} />
          <XAxis
            dataKey={xAxisKey}
            stroke="currentColor"
            fontSize={10}
            tickLine={false}
            className="text-text-muted font-mono"
          />
          <YAxis
            stroke="currentColor"
            fontSize={10}
            tickLine={false}
            className="text-text-muted font-mono"
            tickFormatter={(val) => (typeof val === "number" ? val.toLocaleString() : val)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(15, 23, 42, 0.95)",
              borderColor: "rgba(255, 255, 255, 0.15)",
              borderRadius: "10px",
              fontSize: "11px",
              fontWeight: 600,
              color: "#FFFFFF",
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3)",
            }}
            formatter={(value: any, name: any) => [
              typeof value === "number" ? value.toLocaleString() : value,
              name
            ]}
          />
          {keys.length > 1 && (
            <Legend
              verticalAlign="bottom"
              height={30}
              iconType="circle"
              wrapperStyle={{ fontSize: "11px", fontWeight: 600 }}
            />
          )}

          {keys.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={VIBRANT_LINE_COLORS[index % VIBRANT_LINE_COLORS.length]}
              strokeWidth={2.5}
              activeDot={{ r: 6, strokeWidth: 2 }}
              dot={{ strokeWidth: 2, r: 3.5, fill: "#FFFFFF" }}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
};
