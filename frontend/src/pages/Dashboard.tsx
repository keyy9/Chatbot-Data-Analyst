import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  ShieldCheck,
  Users,
  ArrowUpRight,
  Shield,
  Database,
  RefreshCw,
} from "lucide-react";
import { StatCard } from "../components/StatCard";
import { AnalyticsSummaryPanel } from "../components/AnalyticsSummaryPanel";
import type { QueryLog } from "../types/query";
import type { ManagedUser } from "../types/user";

interface DashboardProps {
  emptySystemState: boolean;
  handleResetData: () => void;
  dashboardStats: {
    totalQueries: number;
    successfulQueries: number;
    failedQueries: number;
    avgResponseTime: number;
    overallAccuracy: number;
    activeSessions: number;
  };
  queryVolumeTrend: any[];
  accuracyHistory: any[];
  queryLogs: QueryLog[];
  managedUsers: ManagedUser[];
  setActiveTab: (tab: any) => void;
  setUserMgmtStatusFilter: (status: any) => void;
  setUserMgmtSearch: (search: string) => void;
  setUserMgmtRoleFilter: (role: any) => void;
  setSelectedLog: (log: QueryLog) => void;
  setActiveKpiModal: (modal: any) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  emptySystemState,
  handleResetData,
  dashboardStats,
  queryVolumeTrend,
  accuracyHistory,
  queryLogs,
  managedUsers,
  setActiveTab,
  setUserMgmtStatusFilter,
  setUserMgmtSearch,
  setUserMgmtRoleFilter,
  setSelectedLog,
  setActiveKpiModal,
}) => {
  if (emptySystemState) {
    return (
      <div className="bg-surface border border-border rounded-2xl p-12 text-center shadow-lg animate-fade-in">
        <div className="w-16 h-16 bg-surface-2 text-text-faint rounded-full flex items-center justify-center mx-auto mb-4 border border-border">
          <Database className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-text mb-1 font-sans">
          No System Data Available
        </h3>
        <p className="text-text-muted text-sm max-w-sm mx-auto mb-6 font-sans">
          The analytical log database is currently empty. Run the database seed
          script or trigger client queries to generate usage metrics.
        </p>
        <button
          type="button"
          onClick={handleResetData}
          className="bg-teal hover:bg-teal-strong text-white font-semibold px-5 py-2.5 rounded-full text-xs transition-all shadow-lg shadow-teal/20 flex items-center gap-2 mx-auto cursor-pointer active:scale-95"
        >
          <RefreshCw className="w-4 h-4" />
          Load Default Datasets
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* STATS CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Total Queries */}
        <StatCard
          title="Total Queries"
          value={dashboardStats.totalQueries}
          icon={<Activity className="w-4 h-4" />}
          subText="↑ 12% vs last week"
          gradientClass="from-[#C04E01] to-[#7A3200]"
          glowClass="shadow-xl hover:shadow-accent/20"
          onClick={() => setActiveKpiModal("total-queries")}
          subTextClass="text-white/85"
        />

        {/* Successful Queries */}
        <StatCard
          title="Successful"
          value={dashboardStats.successfulQueries}
          icon={<CheckCircle className="w-4 h-4" />}
          subText={`${
            dashboardStats.totalQueries > 0
              ? Math.round(
                  (dashboardStats.successfulQueries /
                    dashboardStats.totalQueries) *
                    100
                )
              : 0
          }% success rate`}
          gradientClass="from-[#12403C] to-[#0A2622]"
          glowClass="shadow-xl hover:shadow-teal/20"
          onClick={() => setActiveKpiModal("successful-queries")}
          subTextClass="text-white/85"
        />

        {/* Failed Queries */}
        <StatCard
          title="Failed"
          value={dashboardStats.failedQueries}
          icon={<AlertCircle className="w-4 h-4" />}
          subText="Security blocks"
          gradientClass="from-[#DC2626] to-[#7F1D1D]"
          glowClass="shadow-xl hover:shadow-danger/20"
          onClick={() => setActiveKpiModal("failed-queries")}
          subTextClass="text-white/85"
        />

        {/* Avg Latency */}
        <StatCard
          title="Avg Latency"
          value={`${dashboardStats.avgResponseTime}ms`}
          icon={<Clock className="w-4 h-4" />}
          subText="↓ 8% faster response"
          gradientClass="from-[#1A5A53] to-[#123A34]"
          glowClass="shadow-xl hover:shadow-teal/20"
          onClick={() => setActiveKpiModal("avg-latency")}
          subTextClass="text-white/85"
        />

        {/* SQL Accuracy */}
        <StatCard
          title="SQL Accuracy"
          value={`${dashboardStats.overallAccuracy}%`}
          icon={<ShieldCheck className="w-4 h-4" />}
          subText="From benchmark tests"
          gradientClass="from-[#C99A55] to-[#8A6A2E]"
          glowClass="shadow-xl hover:shadow-sand/20"
          onClick={() => setActiveKpiModal("sql-accuracy")}
          subTextClass="text-white/85"
        />

        {/* Active Users */}
        <StatCard
          title="Active Users"
          value={dashboardStats.activeSessions}
          icon={<Users className="w-4 h-4" />}
          subText="Active analysts"
          gradientClass="from-[#4A5A63] to-[#232E33]"
          glowClass="shadow-xl hover:shadow-grey/20"
          onClick={() => {
            setActiveTab("user-management");
            setUserMgmtStatusFilter("Active");
            setUserMgmtSearch("");
            setUserMgmtRoleFilter("All");
          }}
          subTextClass="text-white/85"
        />
      </div>

      {/* CHARTS GRAPH SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Query Volume Trend */}
        <div className="bg-surface border border-border shadow-lg p-6 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-text font-sans">
                Query Volume Trend
              </h3>
              <p className="text-xs text-text-muted font-semibold mt-0.5 font-sans">
                Analyst request volume over the past 15 days
              </p>
            </div>
            <span className="text-[10px] bg-surface-hover border border-border px-2 py-1 rounded font-bold text-text-muted font-mono">
              Daily Volume
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={queryVolumeTrend}
                margin={{
                  top: 10,
                  right: 10,
                  left: -25,
                  bottom: 0,
                }}
              >
                <defs>
                  <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#12403C" stopOpacity={0.3} />
                    <stop offset="50%" stopColor="#8F00FF" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#00F2FE" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#1B3A38"
                />
                <XAxis
                  dataKey="date"
                  stroke="#94A3B8"
                  fontSize={9}
                  tickLine={false}
                  className="font-mono"
                />
                <YAxis
                  stroke="#94A3B8"
                  fontSize={9}
                  tickLine={false}
                  className="font-mono"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0D1922",
                    border: "1px solid #1B3A38",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#FFFFFF",
                    fontFamily: "sans-serif",
                  }}
                  formatter={(value) => [`${value} queries`, "Volume"]}
                />
                <Area
                  type="monotone"
                  dataKey="queries"
                  stroke="#12403C"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorQueries)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Benchmark Accuracy Trend */}
        <div className="bg-surface border border-border shadow-lg p-6 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-text font-sans">
                Benchmark Accuracy Trend
              </h3>
              <p className="text-xs text-text-muted font-semibold mt-0.5 font-sans">
                SQL generation accuracy score percentage by run history
              </p>
            </div>
            <span className="text-[10px] bg-surface-hover border border-border px-2 py-1 rounded font-bold text-text-muted font-mono">
              Evaluation runs
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={accuracyHistory}
                margin={{
                  top: 10,
                  right: 10,
                  left: -25,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#1B3A38"
                />
                <XAxis
                  dataKey="runId"
                  stroke="#94A3B8"
                  fontSize={9}
                  tickLine={false}
                  className="font-mono"
                />
                <YAxis
                  stroke="#94A3B8"
                  fontSize={9}
                  tickLine={false}
                  domain={[0, 100]}
                  className="font-mono"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0D1922",
                    border: "1px solid #1B3A38",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#FFFFFF",
                    fontFamily: "sans-serif",
                  }}
                  formatter={(value) => [`${value}%`, "Accuracy"]}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#12403C"
                  strokeWidth={2}
                  activeDot={{ r: 5 }}
                  dot={{
                    stroke: "#12403C",
                    strokeWidth: 1.5,
                    r: 3,
                    fill: "#0D1922",
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* BOTTOM PANELS: RECENT ACTIVITY LISTS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel 1: Recent Queries (2/3 width) */}
        <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-bold text-text font-sans">
                Recent User Queries
              </h3>
              <button
                type="button"
                onClick={() => setActiveTab("query-logs")}
                className="text-xs font-bold text-accent hover:text-accent transition-colors flex items-center gap-1 cursor-pointer font-sans"
              >
                View all logs
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="divide-y divide-border/40">
              {queryLogs.slice(0, 5).map((log) => (
                <div
                  key={log.id}
                  className="p-4 hover:bg-surface-hover/30 transition-colors flex items-start justify-between gap-4"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-bold text-text font-sans">
                        {managedUsers.some((u) => u.username === log.user)
                          ? log.user
                          : "Deleted User"}
                      </span>
                      <span className="text-[10px] text-text-faint font-bold font-mono">
                        {new Date(log.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                    <p className="text-xs text-text-muted mt-1 truncate max-w-lg font-mono">
                      {log.question}
                    </p>
                  </div>
                  <div className="flex items-center gap-2.5 flex-shrink-0">
                    <span className="text-[10px] font-bold text-text-muted bg-surface-hover border border-border px-2 py-0.5 rounded font-mono">
                      {log.executionTimeMs}ms
                    </span>
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded-full font-sans ${
                        log.status === "Success"
                          ? "bg-success/10 text-success border border-success/20"
                          : "bg-danger/10 text-danger border border-danger/20"
                      }`}
                    >
                      {log.status}
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedLog(log)}
                      className="text-xs font-bold text-accent hover:text-accent hover:underline px-2 py-1 cursor-pointer font-sans"
                    >
                      Inspect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Panel 2: Recent Benchmark Runs (1/3 width) */}
        <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden">
          <div className="p-5 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-text font-sans">
              Recent Benchmark Runs
            </h3>
            <button
              type="button"
              onClick={() => setActiveTab("benchmark")}
              className="text-xs font-bold text-accent hover:text-accent transition-colors cursor-pointer font-sans"
            >
              Run test
            </button>
          </div>
          <div className="p-4 space-y-4">
            {accuracyHistory
              .slice(-4)
              .reverse()
              .map((run) => (
                <div
                  key={run.runId}
                  className="bg-surface-2 p-3 rounded-lg border border-border flex items-center justify-between"
                >
                  <div>
                    <span className="text-xs font-bold text-text uppercase block font-mono">
                      {run.runId}
                    </span>
                    <span className="text-[9px] text-text-faint font-semibold block mt-0.5 font-mono">
                      {run.timestamp}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-extrabold text-accent block font-mono">
                      {run.accuracy}% Acc
                    </span>
                    <span className="text-[10px] text-text-muted font-semibold block mt-0.5 font-mono">
                      Avg: {run.avgResponseTimeMs}ms
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* USER MANAGEMENT PANELS FOR DASHBOARD INTEGRATION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Recent User Activity (2/3 width) */}
        <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-bold text-text font-sans">
                Recent User Activity
              </h3>
              <button
                type="button"
                onClick={() => setActiveTab("user-management")}
                className="text-xs font-bold text-accent hover:text-accent transition-colors flex items-center gap-1 cursor-pointer font-sans"
              >
                Manage accounts
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="divide-y divide-border/40">
              {managedUsers
                .filter((u) => u.lastActive !== "Never")
                .sort((a, b) => b.lastActive.localeCompare(a.lastActive))
                .slice(0, 4)
                .map((user) => (
                  <div
                    key={user.id}
                    className="p-4 hover:bg-surface-hover/30 transition-colors flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-surface-hover text-text-muted font-extrabold flex items-center justify-center border border-border text-xs font-mono">
                        {user.username.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-text font-sans">
                            {user.username}
                          </span>
                          <span
                            className={`text-[8px] font-bold px-1.5 py-0.2 rounded font-sans ${
                              user.role === "Admin"
                                ? "bg-teal/10 text-teal"
                                : "bg-blue-500/10 text-blue-400"
                            }`}
                          >
                            {user.role}
                          </span>
                        </div>
                        <p className="text-[10px] text-text-faint font-mono mt-0.5">
                          {user.email}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold text-text-muted block font-mono">
                        {user.totalQueries} queries
                      </span>
                      <span className="text-[9px] text-text-faint font-semibold block mt-0.5 font-mono">
                        Last active: {user.lastActive}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* User Role Distribution (1/3 width) */}
        <div className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden flex flex-col justify-between">
          <div>
            <div className="p-5 border-b border-border">
              <h3 className="text-sm font-bold text-text font-sans">
                User Role Distribution
              </h3>
            </div>
            <div className="p-5 space-y-6">
              {/* Admin Role Card */}
              <div className="bg-surface-2/45 border border-border p-4 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-teal/10 rounded-lg border border-teal/20 text-teal">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-text block font-sans">
                      Administrators
                    </span>
                    <span className="text-[10px] text-text-faint font-semibold block mt-0.5 font-sans">
                      Full configuration access
                    </span>
                  </div>
                </div>
                <span className="text-xl font-extrabold text-teal font-mono">
                  {managedUsers.filter((u) => u.role === "Admin").length}
                </span>
              </div>

              {/* User Role Card */}
              <div className="bg-surface-2/45 border border-border p-4 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20 text-blue-400">
                    <Users className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-text block font-sans">
                      Standard Users
                    </span>
                    <span className="text-[10px] text-text-faint font-semibold block mt-0.5 font-sans">
                      Access standard chat
                    </span>
                  </div>
                </div>
                <span className="text-xl font-extrabold text-blue-400 font-mono">
                  {managedUsers.filter((u) => u.role === "User").length}
                </span>
              </div>
            </div>
          </div>

          <div className="p-5 border-t border-border/40 bg-surface-2/25 flex items-center justify-between text-xs font-sans">
            <span className="text-text-muted font-medium">Total Accounts:</span>
            <span className="font-bold text-text font-mono">
              {managedUsers.length}
            </span>
          </div>
        </div>
      </div>

      {/* Real usage analytics (query success rate / execution metrics / error rate) */}
      <AnalyticsSummaryPanel />
    </div>
  );
};
