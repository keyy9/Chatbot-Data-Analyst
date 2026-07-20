import React from "react";
import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface LineChartProps {
  data: Record<string, any>[];
  xAxisKey: string;
  dataKeys: string[];
}

export const LineChart: React.FC<LineChartProps> = ({ data, xAxisKey, dataKeys }) => {
  return (
    <div className="h-48 w-full bg-surface/60 dark:bg-surface/65 border border-slate-200 dark:border-border rounded-xl p-3 shadow-inner">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart
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
          {(dataKeys || []).map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={index % 2 === 0 ? "#00F2FE" : "#12403C"}
              strokeWidth={2}
              activeDot={{ r: 4 }}
              dot={{ strokeWidth: 1.5, r: 2.5 }}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
};
