import React, { useEffect, useState } from "react";
import { X, AlertCircle, CheckCircle } from "lucide-react";
import type { QueryLog } from "../../types/query";
import { adminApi } from "../../lib/apiClient";
import { useAuthStore } from "../../store/authStore";

interface QueryInspectDrawerProps {
  selectedLog: QueryLog | null;
  onClose: () => void;
}

interface LiveResult {
  loading: boolean;
  available: boolean;
  columns: string[];
  rows: Record<string, unknown>[];
  reason?: string;
}

export const QueryInspectDrawer: React.FC<QueryInspectDrawerProps> = ({
  selectedLog,
  onClose,
}) => {
  const userId = useAuthStore((s) => s.user?.userId);
  const [liveResult, setLiveResult] = useState<LiveResult | null>(null);

  // query_logs stores the SQL but not the result rows, so fetch the live
  // output on demand (server re-runs SELECTs read-only). Admin-chat logs that
  // already carry an inline resultPreview skip this.
  useEffect(() => {
    if (!selectedLog || !userId || selectedLog.resultPreview || selectedLog.status === "Failed") {
      setLiveResult(null);
      return;
    }
    let cancelled = false;
    setLiveResult({ loading: true, available: false, columns: [], rows: [] });
    adminApi
      .getQueryLogResult(userId, selectedLog.id)
      .then((res) => {
        if (cancelled) return;
        setLiveResult({
          loading: false,
          available: res.available,
          columns: res.columns || [],
          rows: res.rows || [],
          reason: res.reason,
        });
      })
      .catch(() => {
        if (!cancelled) setLiveResult({ loading: false, available: false, columns: [], rows: [], reason: "Could not load output." });
      });
    return () => { cancelled = true; };
  }, [selectedLog, userId]);

  if (!selectedLog) return null;

  // Prefer an inline preview (admin chat), else the live re-run result.
  const preview = selectedLog.resultPreview
    ? { columns: selectedLog.resultPreview.columns, rows: selectedLog.resultPreview.rows as Record<string, unknown>[] }
    : liveResult?.available
      ? { columns: liveResult.columns, rows: liveResult.rows }
      : null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity duration-300 cursor-pointer"
        onClick={onClose}
      ></div>

      {/* Drawer Inner Content */}
      <div className="relative w-full max-w-2xl bg-surface/95 backdrop-blur-lg border-l border-border h-screen flex flex-col justify-between shadow-2xl z-10 animate-slide-in transition-all duration-300 text-text font-sans">
        <div>
          {/* Drawer Header */}
          <div className="h-16 px-6 border-b border-border flex items-center justify-between bg-surface-2/90">
            <div>
              <h3 className="text-sm font-bold tracking-wide text-text">
                Inspection: Query Details
              </h3>
              <p className="text-[10px] text-text-muted font-semibold mt-0.5 font-mono">
                Log ID: {selectedLog.id}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-text-muted hover:text-text hover:bg-surface-hover rounded-full transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body Scroll */}
          <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-130px)]">
            {/* User details and status banner */}
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wide block font-mono">
                  Triggered By
                </span>
                <span className="text-sm font-bold text-text block mt-1 font-sans">
                  {selectedLog.user}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wide block font-mono">
                  Execution Date
                </span>
                <span className="text-xs font-bold text-text-muted block mt-1 font-mono">
                  {new Date(selectedLog.timestamp).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Guardrails Check Results */}
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider font-mono">
                Security Guardrails check
              </h4>
              {selectedLog.guardrailStatus === "Blocked" ? (
                <div className="bg-red-500/10 border border-red-500/25 p-4 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-red-500 font-bold text-xs font-sans">
                    <AlertCircle className="w-4 h-4 animate-pulse" />
                    Security Exception Triggered (Blocked)
                  </div>
                  {selectedLog.guardrailReason && (
                    <p className="text-xs text-red-400 leading-relaxed font-semibold">
                      Reason: {selectedLog.guardrailReason}
                    </p>
                  )}
                </div>
              ) : (
                <div className="bg-success/10 border border-success/25 p-4 rounded-xl space-y-1">
                  <div className="flex items-center gap-2 text-success font-bold text-xs font-sans">
                    <CheckCircle className="w-4 h-4" />
                    All Policy Guardrails Passed (Allowed)
                  </div>
                  <p className="text-[10px] text-text-faint font-medium font-sans">
                    Query verified against data isolation policies, schema protection, and role permissions.
                  </p>
                </div>
              )}
            </div>

            {/* Natural language question */}
            <div className="space-y-1.5 font-sans">
              <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider font-mono">
                Natural Language Intent
              </h4>
              <p className="text-xs font-bold text-text leading-relaxed bg-surface-2/45 border border-border p-4 rounded-xl shadow-md">
                "{selectedLog.question}"
              </p>
            </div>

            {/* Compiled SQL Dialect */}
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider font-mono">
                Generated SQL query
              </h4>
              <div className="relative border border-border rounded-xl overflow-hidden shadow-md">
                <div className="px-4 py-2 bg-surface-2 border-b border-border flex justify-between items-center text-[10px] text-text-muted font-mono">
                  <span>PostgreSQL Dialect</span>
                </div>
                <pre className="p-4 bg-surface font-mono text-[10px] text-text-muted overflow-x-auto whitespace-pre-wrap leading-normal">
                  <code>{selectedLog.generatedSql}</code>
                </pre>
              </div>
            </div>

            {/* Database result preview */}
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider font-mono">
                Database Output
              </h4>
              {selectedLog.status === "Failed" ? (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-xs font-mono">
                  ⚠️ Query execution failed or blocked by sandbox constraints.
                </div>
              ) : liveResult?.loading ? (
                <div className="bg-surface-2 border border-dashed border-border text-text-faint p-8 rounded-xl text-center text-xs font-sans">
                  Loading live output from the database...
                </div>
              ) : preview && preview.rows.length > 0 ? (
                <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
                  <div className="overflow-x-auto max-h-56 text-xs">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-surface-2 border-b border-border text-text-muted font-bold uppercase text-[9px] tracking-wider font-mono">
                          {preview.columns.map((col, idx) => (
                            <th key={idx} className="py-2.5 px-4">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40 text-text-muted font-mono text-[11px]">
                        {preview.rows.map((row, rowIdx) => (
                          <tr key={rowIdx} className="hover:bg-surface-hover/40">
                            {preview.columns.map((col, colIdx) => (
                              <td key={colIdx} className="py-2.5 px-4 font-medium">
                                {row[col] === null ? "—" : String(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="bg-surface-2 border border-dashed border-border text-text-faint p-8 rounded-xl text-center text-xs font-sans">
                  {liveResult?.reason || "No query output available."}
                </div>
              )}
            </div>

            {/* AI Explanation */}
            {selectedLog.aiExplanation && (
              <div className="space-y-2 font-sans">
                <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider font-mono">
                  Natural Language Explanation
                </h4>
                <p className="text-xs text-text-muted bg-surface-2/45 border border-border p-4 rounded-xl leading-relaxed font-semibold">
                  {selectedLog.aiExplanation}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-border bg-surface-2/90 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text-muted font-bold px-5 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer font-sans"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
