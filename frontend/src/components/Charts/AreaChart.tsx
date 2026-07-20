import React from "react";
import {
  ResponsiveContainer,
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface AreaChartProps {
  data: Record<string, any>[];
  xAxisKey: string;
  dataKeys: string[];
}

export const AreaChart: React.FC<AreaChartProps> = ({ data, xAxisKey, dataKeys }) => {
  return (
    <div className="h-48 w-full bg-surface/60 dark:bg-surface/65 border border-slate-200 dark:border-border rounded-xl p-3 shadow-inner">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart
          data={data}
          margin={{
            top: 5,
            right: 5,
            left: -25,
            bottom: 0,
          }}
        >
          <defs>
            <linearGradient id="chatBubbleAreaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#12403C" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#12403C" stopOpacity={0} />
            </linearGradient>
          </defs>
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
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={index % 2 === 0 ? "#12403C" : "#12403C"}
              strokeWidth={1.5}
              fillOpacity={1}
              fill="url(#chatBubbleAreaFill)"
            />
          ))}
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
};
