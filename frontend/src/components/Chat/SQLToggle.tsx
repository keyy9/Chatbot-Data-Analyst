import React, { useState } from "react";
import { Database, Copy, Check } from "lucide-react";

interface SQLToggleProps {
  sql: string;
  executionTimeMs?: number;
  rowCount?: number;
}

export const SQLToggle: React.FC<SQLToggleProps> = ({ sql, executionTimeMs, rowCount }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-slate-200 dark:border-border rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-950/60 shadow-inner w-full">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-bold text-text-faint dark:text-text-muted hover:text-slate-800 dark:hover:text-text transition-colors uppercase tracking-wider bg-slate-100/60 dark:bg-slate-950/40 cursor-pointer"
      >
        <span className="flex items-center gap-1.5 font-mono">
          <Database className="w-3.5 h-3.5 text-teal" />
          {isOpen ? "Hide SQL Statement" : "Show Generated SQL"}
        </span>
        <span className="text-[9px] font-sans font-normal opacity-70">
          {isOpen ? "Click to collapse" : "Click to expand"}
        </span>
      </button>
      {isOpen && (
        <div className="p-3 border-t border-slate-200 dark:border-border space-y-2 text-left">
          <div className="flex justify-between items-center text-[10px] text-text-faint font-mono">
            <span>
              SQL Dialect: SQLite
              {typeof executionTimeMs === "number" && ` · ${executionTimeMs.toFixed(0)}ms`}
              {typeof rowCount === "number" && ` · ${rowCount} row${rowCount === 1 ? "" : "s"}`}
            </span>
            <button
              onClick={handleCopy}
              className="text-teal hover:text-teal dark:text-teal dark:hover:text-teal flex items-center gap-1 font-bold transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-success" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copy Code
                </>
              )}
            </button>
          </div>
          <pre className="bg-white dark:bg-surface p-3 rounded-lg font-mono text-[10px] text-slate-700 dark:text-text-muted overflow-x-auto border border-slate-100 dark:border-slate-900 leading-normal">
            <code>{sql}</code>
          </pre>
        </div>
      )}
    </div>
  );
};
