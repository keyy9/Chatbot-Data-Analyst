import React, { useEffect, useState } from "react";
import { BarChart3, RefreshCw, AlertTriangle } from "lucide-react";
import { analyticsApi, ApiError } from "../lib/apiClient";
import type { AnalyticsSummary } from "../lib/apiClient";
import { useAuthStore } from "../store/authStore";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

export const AnalyticsSummaryPanel: React.FC = () => {
  const { user } = useAuthStore();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.userId) return;
    setLoading(true);
    analyticsApi
      .getSummary(user.userId)
      .then(setSummary)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load analytics."))
      .finally(() => setLoading(false));
  }, [user?.userId]);

  if (loading) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-text-muted text-xs font-sans">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        Loading real usage analytics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-amber-400 text-xs font-sans">
        <AlertTriangle className="w-3.5 h-3.5" />
        {error}
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl p-5 space-y-5 font-sans">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-bold text-text">Real Usage Analytics</h3>
        </div>
        <span className="text-[10px] text-text-muted font-mono">{summary.total_queries} total queries logged</span>
      </div>
      <p className="text-[11px] text-text-muted -mt-3">
        Aggregated live from the <code className="text-text-muted">query_logs</code> table - every real question asked
        through User Chat and Admin Chat.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-success block">Success Rate</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(summary.success_rate)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-danger block">Error Rate</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(summary.error_rate)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Avg Execution Time</span>
          <span className="text-lg font-extrabold text-text font-mono">
            {summary.avg_execution_time_ms.toFixed(0)}ms
          </span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Token Usage</span>
          <span className="text-sm font-bold text-text-faint">Not tracked</span>
        </div>
      </div>

      <div>
        <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block mb-2">
          Status Breakdown
        </span>
        <div className="flex flex-wrap gap-2">
          {summary.status_breakdown.map((s) => (
            <span
              key={s.status}
              className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-surface-2 border border-border text-text-muted"
            >
              {s.status}: <span className="text-text">{s.count}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
