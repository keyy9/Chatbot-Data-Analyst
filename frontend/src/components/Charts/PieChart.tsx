import React from "react";
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

const COLORS = ["#12403C", "#12403C", "#00F2FE", "#F59E0B", "#10B981"];

export const PieChart: React.FC<PieChartProps> = ({ data, xAxisKey, dataKeys }) => {
  const valueKey = dataKeys[0] || "value";
  const formattedData = data.map(item => ({
    name: item[xAxisKey],
    value: Number(item[valueKey]) || 0
  }));

  return (
    <div className="h-48 w-full bg-surface/60 dark:bg-surface/65 border border-slate-200 dark:border-border rounded-xl p-3 shadow-inner flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          <Tooltip
            contentStyle={{
              backgroundColor: "#0D1922",
              border: "1px solid #1B3A38",
              borderRadius: "8px",
              fontSize: "9px",
              color: "#FFFFFF",
            }}
          />
          <Pie
            data={formattedData}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={65}
            paddingAngle={2}
            dataKey="value"
          >
            {formattedData.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
};
