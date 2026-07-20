import React from "react";
import {
  ResponsiveContainer,
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface BarChartProps {
  data: Record<string, any>[];
  xAxisKey: string;
  dataKeys: string[];
}

export const BarChart: React.FC<BarChartProps> = ({ data, xAxisKey, dataKeys }) => {
  return (
    <div className="h-48 w-full bg-surface/60 dark:bg-surface/65 border border-slate-200 dark:border-border rounded-xl p-3 shadow-inner">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          margin={{
            top: 5,
            right: 5,
            left: -25,
            bottom: 0,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1B3A38" vertical={false} />
          <XAxis
            dataKey={xAxisKey}
            stroke="#94A3B8"
            fontSize={8}
            tickLine={false}
            className="font-mono"
          />
          <YAxis
            stroke="#94A3B8"
            fontSize={8}
            tickLine={false}
            className="font-mono"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0D1922",
              border: "1px solid #1B3A38",
              borderRadius: "8px",
              fontSize: "9px",
              color: "#FFFFFF",
            }}
          />
          {dataKeys.map((key, index) => (
            <Bar
              key={key}
              dataKey={key}
              fill={index % 2 === 0 ? "#12403C" : "#12403C"}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
};
