import React from "react";

interface TableChartProps {
  columns: string[];
  rows: Record<string, any>[];
}

export const TableChart: React.FC<TableChartProps> = ({ columns, rows }) => {
  if (!columns || columns.length === 0) return null;

  return (
    <div className="border border-slate-200 dark:border-border rounded-xl overflow-hidden bg-white dark:bg-surface shadow-md my-3">
      <div className="px-4 py-2 bg-slate-50 dark:bg-surface-2 border-b border-slate-200 dark:border-border flex justify-between items-center">
        <span className="text-[9px] uppercase font-bold text-text-faint dark:text-text-muted tracking-wider">
          Query Results
        </span>
        <span className="text-[9px] font-mono text-text-muted dark:text-text-faint font-semibold">
          {rows.length} row{rows.length === 1 ? "" : "s"} returned
        </span>
      </div>
      <div className="overflow-x-auto max-h-56 text-xs scrollbar-thin">
        <table className="w-full text-left border-collapse font-sans">
          <thead>
            <tr className="bg-slate-50 dark:bg-surface-2 border-b border-slate-200 dark:border-border text-text-faint dark:text-text-muted font-bold uppercase text-[9px] tracking-wider font-mono">
              {columns.map((col, idx) => (
                <th key={idx} className="py-2.5 px-4">
                  {col.replace("_", " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-border/40 text-slate-700 dark:text-text-muted font-mono text-[11px]">
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-slate-50 dark:hover:bg-surface-hover/40 transition-colors">
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className="py-2 px-4 font-medium">
                    {row[col] !== undefined && row[col] !== null ? String(row[col]) : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
