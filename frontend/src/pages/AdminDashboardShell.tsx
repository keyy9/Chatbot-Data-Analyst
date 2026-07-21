import React, { useState, useMemo, useEffect, useCallback } from "react";
import { Navigate } from "react-router-dom";

import type { QueryLog } from "../types/query";
import type { ManagedUser, UserActivity } from "../types/user";

import type { Message as ChatMessage } from "../types";
import { useAuth } from "../hooks/useAuth";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";
import { adminApi, userManagementApi, analyticsApi, evaluationApi, ApiError, type CompareResponse, type AnalyticsSummary } from "../lib/apiClient";
import { mapChartRecommendation, SUPPORTED_CHART_TYPES } from "../lib/chartMapping";
import { mapManagedUser, toApiStatus } from "../lib/userMapping";
import { ComparisonModal } from "../components/Chat/ComparisonModal";

import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import { QueryInspectDrawer } from "../components/drawers/QueryInspectDrawer";
import { KpiDetailsModal } from "../components/modals/KpiDetailsModal";


import { Dashboard } from "./Dashboard";
import { QueryLogs } from "./QueryLogs";
import { UserActivityPage } from "./UserActivity";
import { UserManagement } from "./UserManagement";
import { Benchmark } from "./Benchmark";
import { AdminChat } from "./AdminChat";
import { DbEditor } from "./DbEditor";

export default function App() {
  // Navigation & Page State
  const [activeTab, setActiveTab] = useState<
    | "dashboard"
    | "query-logs"
    | "user-activity"
    | "user-management"
    | "benchmark"
    | "admin-chat"
    | "db-editor"
  >("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Toast Notification State & Helper
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  };

  // Auth Hook integration
  const {
    isAuthenticated,
    handleLogout,
  } = useAuth();

  const { theme, setTheme, modelProvider } = useUiStore();

  const [compareState, setCompareState] = useState<{
    questionText: string;
    isLoading: boolean;
    result: CompareResponse | null;
    error: string | null;
  } | null>(null);

  // All admin data is real (from the backend) - no mock data anywhere.
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [managedUsersLoading, setManagedUsersLoading] = useState(true);

  // Real query log history from the query_logs table.
  const [realQueryLogs, setRealQueryLogs] = useState<QueryLog[]>([]);
  const [realQueryLogsLoading, setRealQueryLogsLoading] = useState(true);

  // Real dashboard analytics (aggregated from query_logs + benchmark evals).
  const [analyticsSummary, setAnalyticsSummary] = useState<AnalyticsSummary | null>(null);
  const [benchmarkAccuracy, setBenchmarkAccuracy] = useState(0);
  const [benchmarkEvalResults, setBenchmarkEvalResults] = useState<{ question: string; status: "correct" | "partial" | "wrong" }[]>([]);
  const [accuracyHistory, setAccuracyHistory] = useState<{ runId: string; accuracy: number; timestamp: string; avgResponseTimeMs: number }[]>([]);
  const [queryVolume, setQueryVolume] = useState<{ date: string; queries: number; successful: number }[]>([]);

  // Retained read-only flags (no simulation toggling - data is always real).
  const [apiError] = useState(false);
  const [emptySystemState] = useState(false);

  // Testing simulation progress states
  const [isTesting] = useState(false);
  // const [testingProgress, setTestingProgress] = useState(0);
  // const [testingCurrentIndex, setTestingCurrentIndex] = useState(-1);

  // KPI modal trigger state
  const [activeKpiModal, setActiveKpiModal] = useState<
    | "total-queries"
    | "successful-queries"
    | "failed-queries"
    | "avg-latency"
    | "sql-accuracy"
    | "active-users"
    | null
  >(null);

  // Detailed inspect drawer trigger state
  const [selectedLog, setSelectedLog] = useState<QueryLog | null>(null);

  // Admin Chat States
  const { user: authUser } = useAuthStore();
  const [adminChatSessionId] = useState(() => crypto.randomUUID());

  // Fetch real query log history
  const loadQueryLogs = useCallback(() => {
    if (!authUser?.userId) return;
    setRealQueryLogsLoading(true);
    adminApi
      .getQueryLogs(authUser.userId)
      .then((res) => setRealQueryLogs(res.logs))
      .catch(() => setRealQueryLogs([]))
      .finally(() => setRealQueryLogsLoading(false));
  }, [authUser?.userId]);

  useEffect(() => { loadQueryLogs(); }, [loadQueryLogs]);

  // Fetch real dashboard analytics (summary + query volume + benchmark accuracy/history)
  const loadAnalytics = useCallback(() => {
    if (!authUser?.userId) return;
    const uid = authUser.userId;
    analyticsApi.getSummary(uid).then(setAnalyticsSummary).catch(() => setAnalyticsSummary(null));
    analyticsApi.getQueryVolume(uid).then((r) => setQueryVolume(r.trend)).catch(() => setQueryVolume([]));
    evaluationApi.getLatestBenchmarkEval(uid)
      .then((r) => {
        setBenchmarkAccuracy(Math.round((r.accuracy_score || 0) * 100));
        setBenchmarkEvalResults(r.results || []);
      })
      .catch(() => { setBenchmarkAccuracy(0); setBenchmarkEvalResults([]); }); // 404 when no runs yet
    evaluationApi.getBenchmarkEvalHistory(uid).then((r) => setAccuracyHistory(r.history)).catch(() => setAccuracyHistory([]));
  }, [authUser?.userId]);

  useEffect(() => { loadAnalytics(); }, [loadAnalytics]);

  // Responsive: auto-collapse the sidebar on small screens.
  useEffect(() => {
    const onResize = () => { if (window.innerWidth < 1024) setSidebarCollapsed(true); };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // User Activity is the real managed-user list, projected into the activity shape.
  const userActivities: UserActivity[] = useMemo(
    () => managedUsers.map((u) => ({
      id: u.id,
      name: u.username,
      email: u.email,
      totalQueries: u.totalQueries,
      loginTime: u.lastActive,
      lastActivity: u.lastActive,
      successRate: u.successRate * 100, // ManagedUser.successRate is 0-1; page renders 0-100
    })),
    [managedUsers]
  );

  // Real user management - fetch once on mount, refetch after every mutation
  // rather than patching local state, so the list (and its query-stat
  // columns) always reflects what the backend actually persisted.
  const refetchManagedUsers = useCallback(() => {
    if (!authUser?.userId) return;
    userManagementApi
      .list(authUser.userId)
      .then((res) => setManagedUsers(res.users.map(mapManagedUser)))
      .catch(() => setManagedUsers([]))
      .finally(() => setManagedUsersLoading(false));
  }, [authUser?.userId]);

  useEffect(() => {
    refetchManagedUsers();
  }, [refetchManagedUsers]);

  const handleCreateManagedUser = async (email: string, username: string, password: string) => {
    if (!authUser?.userId) return { success: false, error: "Not logged in" };
    try {
      await userManagementApi.create(authUser.userId, email, username, password);
      refetchManagedUsers();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof ApiError ? e.message : "Failed to create user" };
    }
  };

  const handleUpdateManagedUsername = async (targetId: string, username: string) => {
    if (!authUser?.userId) return { success: false, error: "Not logged in" };
    try {
      await userManagementApi.updateUsername(authUser.userId, targetId, username);
      refetchManagedUsers();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof ApiError ? e.message : "Failed to update user" };
    }
  };

  const handleUpdateManagedStatus = async (targetId: string, status: ManagedUser["status"]) => {
    if (!authUser?.userId) return { success: false, error: "Not logged in" };
    try {
      await userManagementApi.updateStatus(authUser.userId, targetId, toApiStatus(status));
      refetchManagedUsers();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof ApiError ? e.message : "Failed to update status" };
    }
  };

  const handleTriggerResetPassword = async (targetId: string) => {
    if (!authUser?.userId) return { success: false, error: "Not logged in" };
    try {
      const res = await userManagementApi.triggerResetPassword(authUser.userId, targetId);
      return { success: true, message: res.message };
    } catch (e) {
      return { success: false, error: e instanceof ApiError ? e.message : "Failed to send reset email" };
    }
  };

  const handleDeleteManagedUser = async (targetId: string) => {
    if (!authUser?.userId) return { success: false, error: "Not logged in" };
    try {
      await userManagementApi.deleteUser(authUser.userId, targetId);
      refetchManagedUsers();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof ApiError ? e.message : "Failed to delete user" };
    }
  };

  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "ai",
      text: "Hello! I am your AI Data Analyst assistant with administrative database privileges. Ask me anything about our database, or perform data operations (INSERT, UPDATE, DELETE). For example, try asking 'Show all products in the store' or 'Delete all orders with cancelled status'.",
      timestamp: Date.now(),
    },
  ]);

  // Search filter sharing states for dashboard click navigation
  const [userMgmtSearch, setUserMgmtSearch] = useState("");
  const [userMgmtRoleFilter, setUserMgmtRoleFilter] = useState<"All" | "Admin" | "User">("All");
  const [userMgmtStatusFilter, setUserMgmtStatusFilter] = useState<"All" | "Active" | "Inactive" | "Suspended">("All");
  const [userMgmtSortCol, setUserMgmtSortCol] = useState<"username" | "lastActive" | "none">("none");
  const [userMgmtSortOrder, setUserMgmtSortOrder] = useState<"asc" | "desc">("asc");
  const [userMgmtCurrentPage, setUserMgmtCurrentPage] = useState(1);

  // Refresh all dashboard data from the database.
  const handleResetData = () => {
    refetchManagedUsers();
    loadQueryLogs();
    loadAnalytics();
    showToast("🔄 Dashboard refreshed from the database.");
  };

  // Dashboard KPI cards - all from real backend data (analytics summary +
  // benchmark accuracy + managed users).
  const dashboardStats = useMemo(() => {
    const activeManagedCount = managedUsers.filter((u) => u.status === "Active").length;

    return {
      totalQueries: analyticsSummary?.total_queries ?? 0,
      successfulQueries: analyticsSummary?.successful_queries ?? 0,
      failedQueries: analyticsSummary?.failed_queries ?? 0,
      avgResponseTime: Math.round(analyticsSummary?.avg_execution_time_ms ?? 0),
      overallAccuracy: benchmarkAccuracy,
      activeSessions: activeManagedCount,
    };
  }, [analyticsSummary, benchmarkAccuracy, managedUsers]);

  // Admin Chat Submit Handler - real NL-to-SQL pipeline via /api/admin/ask
  const handleAdminChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput || apiError) return;

    const userId = authUser?.userId;
    const userQuestion = chatInput;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      sender: "user",
      text: userQuestion,
      timestamp: Date.now(),
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");

    if (!userId) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: "You're not logged in as an admin. Please sign in again.",
          timestamp: Date.now(),
          status: "Failed",
        },
      ]);
      return;
    }

    setIsChatLoading(true);

    try {
      const res = await adminApi.ask(userQuestion, userId, adminChatSessionId, modelProvider);

      let aiMsg: ChatMessage;

      if (res.status === "clarification_needed") {
        aiMsg = {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: res.explanation,
          timestamp: Date.now(),
          isClarification: true,
          clarificationOptions: res.options,
          provider: res.model_provider,
          modelName: res.model_name,
        };
      } else if (res.status === "pending_confirmation") {
        aiMsg = {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: `I generated a ${res.operation.toUpperCase()} statement. Review it below and confirm to actually run it against the database.`,
          timestamp: Date.now(),
          sql: res.generated_sql,
          pendingConfirmation: {
            token: res.token,
            operation: res.operation,
            sqlPreview: res.sql_preview,
            expiresAt: res.expires_at,
          },
          provider: res.model_provider,
          modelName: res.model_name,
        };
      } else {
        aiMsg = {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: res.explanation,
          timestamp: Date.now(),
          status: "Success",
          sql: res.generated_sql,
          message: `Query OK, ${res.data.length} row(s) returned.`,
          resultPreview: res.data.length > 0 ? { columns: res.columns, rows: res.data } : undefined,
          chartData: mapChartRecommendation(
            (res.chart_recommendation as { type?: string })?.type,
            res.data,
            res.columns,
            SUPPORTED_CHART_TYPES
          ),
          provider: res.model_provider,
          modelName: res.model_name,
        };
      }

      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: "Failed to execute the administrative query.",
          timestamp: Date.now(),
          status: "Failed",
          message,
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Confirm & execute a previously proposed write (INSERT/UPDATE/DELETE)
  const handleConfirmWrite = async (messageId: string, token: string) => {
    const userId = authUser?.userId;
    if (!userId) return;

    setIsChatLoading(true);
    try {
      const res = await adminApi.confirm(token, userId, adminChatSessionId);
      setChatMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                pendingConfirmation: m.pendingConfirmation
                  ? { ...m.pendingConfirmation, resolved: "confirmed" as const }
                  : undefined,
                status: "Success" as const,
                message: `Query OK, ${res.affected_rows} row(s) affected.`,
                resultPreview: res.data.length > 0 ? { columns: Object.keys(res.data[0]), rows: res.data } : undefined,
              }
            : m
        )
      );

      // Automatically append refreshed SELECT result message if present!
      if (res.refreshed_data) {
        const refreshedMsg: ChatMessage = {
          id: `msg-${Date.now()}-refreshed`,
          sender: "ai",
          text: `Refreshed results reflecting the latest database state for: "${res.refreshed_data.question}"`,
          timestamp: Date.now(),
          status: "Success",
          sql: res.refreshed_data.sql,
          message: `Query OK, ${res.refreshed_data.data.length} row(s) returned.`,
          resultPreview: res.refreshed_data.data.length > 0 
            ? { columns: res.refreshed_data.columns, rows: res.refreshed_data.data } 
            : undefined,
          chartData: mapChartRecommendation(
            res.refreshed_data.chart_type,
            res.refreshed_data.data,
            res.refreshed_data.columns,
            SUPPORTED_CHART_TYPES
          )
        };
        setChatMessages((prev) => [...prev, refreshedMsg]);
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to confirm the write.";
      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}-ai`,
          sender: "ai",
          text: "Failed to execute the confirmed statement.",
          timestamp: Date.now(),
          status: "Failed",
          message,
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleAdminClarificationOption = (option: string) => {
    setChatInput(option);
  };

  const handleAdminCompare = async (questionText: string) => {
    const userId = authUser?.userId;
    if (!userId) return;

    setCompareState({ questionText, isLoading: true, result: null, error: null });
    try {
      const result = await adminApi.askCompare(questionText, userId, adminChatSessionId);
      setCompareState({ questionText, isLoading: false, result, error: null });
    } catch {
      setCompareState({ questionText, isLoading: false, result: null, error: "Comparison failed. Please try again." });
    }
  };

  // Render Login overlay first if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="h-screen overflow-hidden flex font-sans selection:bg-accent/20 selection:text-accent bg-bg text-text">
      {/* TOAST NOTIFICATION CONTAINER */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-[100] bg-surface border border-accent/30 text-text px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-rise-in glass-panel">
          <span className="text-xs font-bold font-sans">{toastMessage}</span>
        </div>
      )}

      {/* SIDEBAR NAVIGATION */}
      <Sidebar
        theme={theme}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        isTesting={isTesting}
      />

      {/* MAIN CONTAINER */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* TOP NAVIGATION BAR */}
        <Header
          theme={theme}
          setTheme={setTheme}
          activeTab={activeTab}
          apiError={apiError}
          handleLogout={handleLogout}
        />

        {/* WORKSPACE CONTENT BODY */}
        <section className="flex-1 overflow-y-auto p-6">
          {activeTab === "dashboard" && (
            <Dashboard
              emptySystemState={emptySystemState}
              handleResetData={handleResetData}
              dashboardStats={dashboardStats}
              queryVolumeTrend={queryVolume}
              accuracyHistory={accuracyHistory}
              queryLogs={realQueryLogs}
              managedUsers={managedUsers}
              setActiveTab={setActiveTab}
              setUserMgmtStatusFilter={setUserMgmtStatusFilter}
              setUserMgmtSearch={setUserMgmtSearch}
              setUserMgmtRoleFilter={setUserMgmtRoleFilter}
              setSelectedLog={setSelectedLog}
              setActiveKpiModal={setActiveKpiModal}
            />
          )}

          {activeTab === "query-logs" && (
            realQueryLogsLoading ? (
              <div className="bg-surface border border-border shadow-lg p-8 rounded-2xl text-center text-text-muted text-xs font-sans">
                Loading query logs...
              </div>
            ) : (
              <QueryLogs
                queryLogs={realQueryLogs}
                setSelectedLog={setSelectedLog}
              />
            )
          )}

          {activeTab === "user-activity" && (
            <UserActivityPage
              userActivities={userActivities}
            />
          )}

          {activeTab === "user-management" && (
            <UserManagement
              managedUsers={managedUsers}
              managedUsersLoading={managedUsersLoading}
              onCreateUser={handleCreateManagedUser}
              onUpdateUsername={handleUpdateManagedUsername}
              onUpdateStatus={handleUpdateManagedStatus}
              onTriggerResetPassword={handleTriggerResetPassword}
              onDeleteUser={handleDeleteManagedUser}
              userMgmtSearch={userMgmtSearch}
              setUserMgmtSearch={setUserMgmtSearch}
              userMgmtRoleFilter={userMgmtRoleFilter}
              setUserMgmtRoleFilter={setUserMgmtRoleFilter}
              userMgmtStatusFilter={userMgmtStatusFilter}
              setUserMgmtStatusFilter={setUserMgmtStatusFilter}
              userMgmtSortCol={userMgmtSortCol}
              setUserMgmtSortCol={setUserMgmtSortCol}
              userMgmtSortOrder={userMgmtSortOrder}
              setUserMgmtSortOrder={setUserMgmtSortOrder}
              userMgmtCurrentPage={userMgmtCurrentPage}
              setUserMgmtCurrentPage={setUserMgmtCurrentPage}
              userMgmtPerPage={8}
              showToast={showToast}
            />
          )}

          {activeTab === "benchmark" && (
            <Benchmark />
          )}

          {activeTab === "admin-chat" && (
            <AdminChat
              chatMessages={chatMessages}
              setChatMessages={setChatMessages}
              isChatLoading={isChatLoading}
              chatInput={chatInput}
              setChatInput={setChatInput}
              handleAdminChatSubmit={handleAdminChatSubmit}
              handleConfirmWrite={handleConfirmWrite}
              handleClarificationOption={handleAdminClarificationOption}
              onCompare={handleAdminCompare}
            />
          )}

          {activeTab === "db-editor" && (
            <DbEditor
              userId={authUser?.userId || ""}
              sessionId={adminChatSessionId}
            />
          )}
        </section>
      </main>

      {/* DETAILED INSPECT DRAWER */}
      <QueryInspectDrawer
        selectedLog={selectedLog}
        onClose={() => setSelectedLog(null)}
      />

      {/* KPI DETAIL MODALS */}
      <KpiDetailsModal
        activeKpiModal={activeKpiModal}
        onClose={() => setActiveKpiModal(null)}
        queryLogs={realQueryLogs}
        userActivities={userActivities}
        benchmarkQuestions={benchmarkEvalResults.map((r, i) => ({
          id: String(i),
          question: r.question,
          expectedSql: "",
          result: r.status === "correct" ? "Correct" : "Incorrect",
        }))}
      />

      {/* Per-query model comparison modal */}
      {compareState && (
        <ComparisonModal
          questionText={compareState.questionText}
          isLoading={compareState.isLoading}
          result={compareState.result}
          error={compareState.error}
          onClose={() => setCompareState(null)}
        />
      )}
    </div>
  );
}
