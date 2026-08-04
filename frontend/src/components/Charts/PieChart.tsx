import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

interface PieChartProps {
  data: Record<string, any>[];
  xAxisKey: string; // name key
  dataKeys: string[]; // value keys
}

// Vibrant, distinct high-contrast color palette visible on both dark & light backgrounds
const VIBRANT_PIE_COLORS = [
  "#F97316", // Vibrant Orange
  "#06B6D4", // Bright Cyan
  "#8B5CF6", // Vivid Purple
  "#10B981", // Emerald Green
  "#F59E0B", // Amber Gold
  "#EC4899", // Bright Pink
  "#3B82F6", // Royal Blue
  "#84CC16", // Bright Lime
  "#E11D48", // Crimson Rose
  "#6366F1", // Indigo
];

export const PieChart: React.FC<PieChartProps> = ({ data, xAxisKey, dataKeys }) => {
  const valueKey = (dataKeys && dataKeys[0]) || "value";

  // Process data: aggregate into Top 6 + "Other" if too many items
  const { chartData, totalValue } = useMemo(() => {
    const rawData = data.map((item) => ({
      name: String(item[xAxisKey] ?? "Unknown"),
      value: Math.max(0, Number(item[valueKey]) || 0),
    }));

    const total = rawData.reduce((acc, curr) => acc + curr.value, 0);

    // Sort descending
    const sorted = [...rawData].sort((a, b) => b.value - a.value);

    // If items count <= 7, use as is
    if (sorted.length <= 7) {
      return { chartData: sorted, totalValue: total };
    }

    // Keep top 6 and aggregate remainder into "Other"
    const top6 = sorted.slice(0, 6);
    const remainder = sorted.slice(6);
    const otherSum = remainder.reduce((acc, curr) => acc + curr.value, 0);

    if (otherSum > 0) {
      top6.push({
        name: `Other (${remainder.length} items)`,
        value: otherSum,
      });
    }

    return { chartData: top6, totalValue: total };
  }, [data, xAxisKey, valueKey]);

  return (
    <div className="w-full bg-surface-2/80 border border-border rounded-xl p-3.5 shadow-xs flex flex-col md:flex-row items-center gap-3 font-sans transition-all">
      {/* Pie Chart Visual Container */}
      <div className="h-52 w-full md:w-1/2 flex items-center justify-center relative">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPieChart>
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
                typeof value === "number"
                  ? `${value.toLocaleString()} (${totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) : 0}%)`
                  : value,
                name,
              ]}
            />
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={38}
              outerRadius={68}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((_entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={VIBRANT_PIE_COLORS[index % VIBRANT_PIE_COLORS.length]}
                  stroke="rgba(0, 0, 0, 0.2)"
                  strokeWidth={1.5}
                />
              ))}
            </Pie>
          </RechartsPieChart>
        </ResponsiveContainer>
      </div>

      {/* Custom Scrollable Responsive Legend */}
      <div className="w-full md:w-1/2 max-h-48 overflow-y-auto pr-1 space-y-1.5 font-sans">
        <div className="flex items-center justify-between border-b border-border/40 pb-1 mb-1">
          <span className="text-[10px] font-extrabold uppercase text-text-muted tracking-wider">
            Breakdown ({data.length} items)
          </span>
          <span className="text-[10px] font-mono font-bold text-teal">
            Total: {totalValue.toLocaleString()}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-1.5">
          {chartData.map((entry, idx) => {
            const color = VIBRANT_PIE_COLORS[idx % VIBRANT_PIE_COLORS.length];
            const pct = totalValue > 0 ? ((entry.value / totalValue) * 100).toFixed(1) : "0";

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-1.5 rounded-lg bg-surface/60 border border-border/50 hover:border-teal/40 text-xs transition-colors gap-2 group"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0 shadow-xs"
                    style={{ backgroundColor: color }}
                  />
                  <span className="font-bold text-text group-hover:text-teal transition-colors truncate text-[11px]" title={entry.name}>
                    {entry.name}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 font-mono text-[10px]">
                  <span className="text-text font-bold">{entry.value.toLocaleString()}</span>
                  <span className="text-text-muted px-1 rounded bg-surface-hover font-bold">
                    {pct}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
