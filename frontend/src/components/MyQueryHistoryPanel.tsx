import React, { useEffect, useState } from "react";
import { History, RefreshCw, AlertTriangle } from "lucide-react";
import { userApi, ApiError } from "../lib/apiClient";
import type { QueryLog } from "../types/query";
import { useAuthStore } from "../store/authStore";

export const MyQueryHistoryPanel: React.FC = () => {
  const { user } = useAuthStore();
  const [logs, setLogs] = useState<QueryLog[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.userId) return;
    setLoading(true);
    userApi
      .getMyQueryLogs(user.userId)
      .then((res) => setLogs(res.logs))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load query history."))
      .finally(() => setLoading(false));
  }, [user?.userId]);

  return (
    <div className="p-6 rounded-2xl border shadow-md text-left space-y-4 bg-surface border-border">
      <h3 className="text-sm font-bold text-white flex items-center gap-2">
        <History className="w-4 h-4 text-teal" />
        My Query History
      </h3>

      {loading && (
        <div className="flex items-center gap-2 text-text-muted text-xs">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          Loading your query history...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-amber-400 text-xs">
          <AlertTriangle className="w-3.5 h-3.5" />
          {error}
        </div>
      )}

      {logs && logs.length === 0 && (
        <p className="text-xs text-text-faint">You haven't asked any questions yet.</p>
      )}

      {logs && logs.length > 0 && (
        <div className="divide-y divide-border/40">
          {logs.map((log) => (
            <div key={log.id} className="py-3 space-y-1">
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold text-text truncate">{log.question}</span>
                <span
                  className={`text-[9px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${
                    log.status === "Success"
                      ? "bg-success/10 text-success border border-success/20"
                      : "bg-danger/10 text-danger border border-danger/20"
                  }`}
                >
                  {log.status}
                </span>
              </div>
              <div className="flex items-center justify-between text-[9px] font-mono text-text-faint">
                <span>{log.executionTimeMs}ms</span>
                <span>{new Date(log.timestamp).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
