import React from "react";
import { TrendingUp } from "lucide-react";
import type { QueryLog } from "../../types/query";
import type { ManagedUser, UserActivity } from "../../types/user";
import type { BenchmarkQuestion } from "../../types/benchmark";
import { Modal } from "../Modal";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

interface KpiDetailsModalProps {
  activeKpiModal:
    | "total-queries"
    | "successful-queries"
    | "failed-queries"
    | "avg-latency"
    | "sql-accuracy"
    | "active-users"
    | null;
  onClose: () => void;
  queryLogs: QueryLog[];
  managedUsers: ManagedUser[];
  userActivities: UserActivity[];
  benchmarkQuestions: BenchmarkQuestion[];
}

export const KpiDetailsModal: React.FC<KpiDetailsModalProps> = ({
  activeKpiModal,
  onClose,
  queryLogs,
  managedUsers,
  userActivities,
  benchmarkQuestions,
}) => {
  if (!activeKpiModal) return null;

  return (
    <Modal
      isOpen={!!activeKpiModal}
      onClose={onClose}
      title={`${activeKpiModal.replace("-", " ")} Details`}
      icon={<TrendingUp className="w-4 h-4 text-accent" />}
      maxWidthClass="max-w-3xl"
    >
      <div className="p-6 overflow-y-auto max-h-[70vh] space-y-4 font-sans text-text">
        {/* Render content depending on active KPI modal type */}
        {activeKpiModal === "total-queries" && (
          <div className="space-y-4">
            <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
              All Simulated Query History
            </h4>
            <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
              <div className="overflow-x-auto text-[11px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border text-text-faint font-bold uppercase text-[8px] tracking-wider font-mono">
                      <th className="py-2 px-4">User</th>
                      <th className="py-2 px-4">Question</th>
                      <th className="py-2 px-4">Latency</th>
                      <th className="py-2 px-4">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {queryLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-surface-hover/40">
                        <td className="py-2 px-4 font-bold text-text">
                          {managedUsers.some((u) => u.username === log.user)
                            ? log.user
                            : "Deleted User"}
                        </td>
                        <td className="py-2 px-4 truncate max-w-xs text-text-muted font-medium">
                          {log.question}
                        </td>
                        <td className="py-2 px-4 font-bold text-text-muted font-mono">
                          {log.executionTimeMs}ms
                        </td>
                        <td className="py-2 px-4 text-text-faint font-mono">
                          {log.timestamp.split("T")[0]}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeKpiModal === "successful-queries" && (
          <div className="space-y-4">
            <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
              Successful Query Transactions
            </h4>
            <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
              <div className="overflow-x-auto text-[11px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border text-text-faint font-bold uppercase text-[8px] tracking-wider font-mono">
                      <th className="py-2 px-4">User</th>
                      <th className="py-2 px-4">Question</th>
                      <th className="py-2 px-4 font-sans">Status</th>
                      <th className="py-2 px-4">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {queryLogs
                      .filter((log) => log.status === "Success")
                      .map((log) => (
                        <tr key={log.id} className="hover:bg-surface-hover/40">
                          <td className="py-2 px-4 font-bold text-text">
                            {managedUsers.some((u) => u.username === log.user)
                              ? log.user
                              : "Deleted User"}
                          </td>
                          <td className="py-2 px-4 truncate max-w-xs text-text-muted font-medium">
                            {log.question}
                          </td>
                          <td className="py-2 px-4 text-success font-bold">
                            Success
                          </td>
                          <td className="py-2 px-4 text-text-faint font-mono">
                            {log.timestamp.split("T")[0]}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeKpiModal === "failed-queries" && (
          <div className="space-y-4">
            <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
              Failed or Blocked Queries
            </h4>
            <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
              <div className="overflow-x-auto text-[11px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border text-text-faint font-bold uppercase text-[8px] tracking-wider font-mono">
                      <th className="py-2 px-4">User</th>
                      <th className="py-2 px-4">Question</th>
                      <th className="py-2 px-4 font-sans">Status</th>
                      <th className="py-2 px-4">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {queryLogs
                      .filter((log) => log.status === "Failed")
                      .map((log) => (
                        <tr key={log.id} className="hover:bg-surface-hover/40">
                          <td className="py-2 px-4 font-bold text-text">
                            {managedUsers.some((u) => u.username === log.user)
                              ? log.user
                              : "Deleted User"}
                          </td>
                          <td className="py-2 px-4 truncate max-w-xs text-text-muted font-medium">
                            {log.question}
                          </td>
                          <td className="py-2 px-4 text-red-500 font-bold">
                            Failed
                          </td>
                          <td className="py-2 px-4 text-text-faint font-mono">
                            {log.timestamp.split("T")[0]}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeKpiModal === "avg-latency" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-center font-mono">
              <div className="bg-surface-2 border border-border p-3 rounded-lg">
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wider block">
                  Min Latency
                </span>
                <span className="text-lg font-bold text-text block mt-1">
                  {queryLogs.length > 0
                    ? Math.min(...queryLogs.map((l) => l.executionTimeMs))
                    : 0}
                  ms
                </span>
              </div>
              <div className="bg-surface-2 border border-border p-3 rounded-lg">
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wider block">
                  Max Latency
                </span>
                <span className="text-lg font-bold text-text block mt-1">
                  {queryLogs.length > 0
                    ? Math.max(...queryLogs.map((l) => l.executionTimeMs))
                    : 0}
                  ms
                </span>
              </div>
            </div>
            <div className="h-48 w-full bg-surface border border-border rounded-xl p-3 shadow-md">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={[...queryLogs].reverse()}
                  margin={{
                    top: 5,
                    right: 5,
                    left: -25,
                    bottom: 0,
                  }}
                >
                  <defs>
                    <linearGradient
                      id="modalLatencyColor"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor="#12403C"
                        stopOpacity={0.2}
                      />
                      <stop
                        offset="95%"
                        stopColor="#12403C"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1B3A38" />
                  <XAxis dataKey="id" stroke="#94A3B8" fontSize={8} />
                  <YAxis stroke="#94A3B8" fontSize={8} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0D1922",
                      border: "1px solid #1B3A38",
                      fontSize: "9px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="executionTimeMs"
                    stroke="#12403C"
                    fill="url(#modalLatencyColor)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeKpiModal === "sql-accuracy" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-center font-mono">
              <div className="bg-surface-2 border border-border p-3 rounded-lg">
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wider block font-sans">
                  Correct Evaluations
                </span>
                <span className="text-lg font-bold text-success block mt-1">
                  {
                    benchmarkQuestions.filter((q) => q.result === "Correct")
                      .length
                  }
                </span>
              </div>
              <div className="bg-surface-2 border border-border p-3 rounded-lg">
                <span className="text-[9px] font-bold text-text-faint uppercase tracking-wider block font-sans">
                  Incorrect Evaluations
                </span>
                <span className="text-lg font-bold text-red-500 block mt-1">
                  {
                    benchmarkQuestions.filter((q) => q.result === "Incorrect")
                      .length
                  }
                </span>
              </div>
            </div>
            <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
              <div className="overflow-x-auto text-[11px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border text-text-faint font-bold uppercase text-[8px] tracking-wider font-mono">
                      <th className="py-2 px-4">Evaluation Result</th>
                      <th className="py-2 px-4">Question Target</th>
                      <th className="py-2 px-4 font-sans">Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {benchmarkQuestions.map((bq) => (
                      <tr key={bq.id} className="hover:bg-surface-hover/40">
                        <td className="py-2 px-4">
                          <span
                            className={`font-bold px-2 py-0.5 rounded text-[8px] font-sans ${
                              bq.result === "Correct"
                                ? "bg-success/10 text-success"
                                : bq.result === "Incorrect"
                                  ? "bg-danger/10 text-danger"
                                  : "bg-slate-800 text-text-muted"
                            }`}
                          >
                            {bq.result || "Pending"}
                          </span>
                        </td>
                        <td className="py-2 px-4 truncate max-w-xs text-text-muted font-semibold">
                          {bq.question}
                        </td>
                        <td className="py-2 px-4 font-mono font-semibold">
                          {bq.responseTimeMs ? `${bq.responseTimeMs}ms` : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeKpiModal === "active-users" && (
          <div className="space-y-4">
            <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
              Active Analyst Sessions
            </h4>
            <div className="border border-border rounded-xl overflow-hidden bg-surface shadow-md">
              <div className="overflow-x-auto text-[11px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border text-text-faint font-bold uppercase text-[8px] tracking-wider font-mono">
                      <th className="py-2 px-4">Analyst</th>
                      <th className="py-2 px-4">Email</th>
                      <th className="py-2 px-4">Success Rate</th>
                      <th className="py-2 px-4">Last Activity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {userActivities.map((user) => (
                      <tr key={user.id} className="hover:bg-surface-hover/40">
                        <td className="py-2 px-4 font-bold text-text">
                          {user.name}
                        </td>
                        <td className="py-2 px-4 font-mono text-text-faint">
                          {user.email ||
                            `${user.name
                              .toLowerCase()
                              .replace(" ", "")}@lapisai.com`}
                        </td>
                        <td className="py-2 px-4 font-bold font-mono text-accent">
                          {user.successRate.toFixed(1)}%
                        </td>
                        <td className="py-2 px-4 text-text-muted font-mono">
                          {user.lastActivity}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-6 py-4 border-t border-border bg-surface-2/45 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text-muted font-bold px-4 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer font-sans"
        >
          Close Detail
        </button>
      </div>
    </Modal>
  );
};
