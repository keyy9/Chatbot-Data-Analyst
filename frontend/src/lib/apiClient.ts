import type { PipelineEvalRun, BenchmarkEvalRun } from "../types/benchmark";
import type { QueryLog } from "../types/query";
import type { ModelProvider } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8005";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, body: unknown, method = "POST"): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch {
    throw new ApiError(0, "Could not reach the AI backend. Is it running?");
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, payload.detail || "Request failed");
  }

  return payload as T;
}

async function requestGet<T>(path: string, params: Record<string, string>): Promise<T> {
  let response: Response;
  const query = new URLSearchParams(params).toString();

  try {
    response = await fetch(`${API_BASE_URL}${path}?${query}`);
  } catch {
    throw new ApiError(0, "Could not reach the AI backend. Is it running?");
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, payload.detail || "Request failed");
  }

  return payload as T;
}

// ============ Auth ============

export interface LoginResponse {
  requires_otp: boolean;
  user_id: string;
  email?: string;
  username?: string | null;
  role?: "user" | "admin";
  message?: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/auth/login", { email, password }),
  verifyOtp: (user_id: string, otp_code: string) =>
    request<LoginResponse>("/api/auth/verify-otp", { user_id, otp_code }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/auth/forgot-password", { email }),
  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>("/api/auth/reset-password", { token, new_password }),
  changePassword: (email: string, current_password: string, new_password: string) =>
    request<{ message: string }>("/api/auth/change-password", { email, current_password, new_password }),
  getProfile: (user_id: string) =>
    requestGet<AccountProfile>("/api/auth/profile", { user_id }),
  updateProfile: (user_id: string, username: string) =>
    request<AccountProfile>("/api/auth/profile", { user_id, username })
};

export interface AccountProfile {
  user_id: string;
  email: string;
  username: string | null;
  role: "user" | "admin";
  created_at: string | null;
}

// ============ Admin User Management ============

export interface ManagedUserApiShape {
  id: string;
  email: string;
  username: string | null;
  role: "user" | "admin";
  status: "active" | "inactive" | "suspended";
  last_login_at: string | null;
  created_at: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
}

export const userManagementApi = {
  list: (user_id: string) =>
    requestGet<{ users: ManagedUserApiShape[] }>("/api/admin/users", { user_id }),
  create: (user_id: string, email: string, username: string, password: string) =>
    request<ManagedUserApiShape>("/api/admin/users/create", { user_id, email, username, password }),
  updateUsername: (user_id: string, target_id: string, username: string) =>
    request<{ message: string }>("/api/admin/users/update", { user_id, target_id, username }),
  updateStatus: (user_id: string, target_id: string, status: ManagedUserApiShape["status"]) =>
    request<{ message: string }>("/api/admin/users/status", { user_id, target_id, status }),
  triggerResetPassword: (user_id: string, target_id: string) =>
    request<{ message: string }>("/api/admin/users/reset-password", { user_id, target_id }),
  deleteUser: (user_id: string, target_id: string) =>
    request<{ message: string }>("/api/admin/users/delete", { user_id, target_id })
};

// ============ Shared question/answer shapes ============

export interface ChartRecommendation {
  type: string;
  confidence: number;
  reason: string;
  alternatives: string[];
  configuration: Record<string, unknown>;
}

export interface AskSuccessResponse {
  status: "success";
  generated_sql: string;
  explanation: string;
  chart_recommendation: ChartRecommendation | Record<string, never>;
  sources: Record<string, unknown>;
  data: Record<string, unknown>[];
  columns: string[];
  metadata: { query_execution_time_ms?: number } & Record<string, unknown>;
  model_provider: ModelProvider;
  model_name: string;
}

export interface AskClarificationResponse {
  status: "clarification_needed";
  explanation: string;
  options: string[];
  model_provider: ModelProvider;
  model_name: string;
}

export type UserAskResponse = AskSuccessResponse | AskClarificationResponse;

// ============ Per-query model comparison (POST /ask/compare) ============

export interface RawProviderCompareResult {
  provider: ModelProvider;
  model_name: string;
  status: "success" | "clarification_needed" | "error" | "write_preview";
  operation?: string;
  generated_sql?: string;
  explanation?: string;
  chart_recommendation?: Record<string, unknown>;
  data?: Record<string, unknown>[];
  columns?: string[];
  options?: string[];
  error?: string;
  latency_ms: number;
}

export interface CompareResponse {
  results: {
    groq: RawProviderCompareResult;
    gemini: RawProviderCompareResult;
  };
}

// ============ User (read-only) chat ============

export const userApi = {
  ask: (question: string, user_id: string, session_id: string, model_provider: ModelProvider = "groq") =>
    request<UserAskResponse>("/api/user/ask", { question, user_id, session_id, model_provider }),
  askCompare: (question: string, user_id: string, session_id: string) =>
    request<CompareResponse>("/api/user/ask/compare", { question, user_id, session_id }),
  getMyQueryLogs: (user_id: string) =>
    requestGet<{ logs: QueryLog[] }>("/api/user/query-logs", { user_id }),

  // DB-persisted chat sessions & messages
  getSessions: (user_id: string) =>
    requestGet<{ sessions: { id: string; title: string; createdAt: number }[] }>("/api/user/sessions", { user_id }),
  createSession: (user_id: string, id: string, title: string) =>
    request<{ status: string; session_id: string }>("/api/user/sessions", { user_id, id, title }),
  renameSession: (user_id: string, id: string, title: string) =>
    request<{ status: string }>("/api/user/sessions/rename", { user_id, id, title }),
  deleteSession: (user_id: string, session_id: string) =>
    request<{ status: string }>(`/api/user/sessions/${session_id}`, { user_id }, "DELETE"),
  getSessionMessages: (user_id: string, session_id: string) =>
    requestGet<{ messages: any[] }>(`/api/user/sessions/${session_id}/messages`, { user_id })
};

// ============ Admin chat (read + propose/confirm writes) ============

export interface AdminAskPendingConfirmation {
  status: "pending_confirmation";
  operation: string;
  generated_sql: string;
  token: string;
  sql_preview: string;
  expires_at: string;
  model_provider: ModelProvider;
  model_name: string;
}

export type AdminAskResponse = AskSuccessResponse | AskClarificationResponse | AdminAskPendingConfirmation;

export interface AdminConfirmResponse {
  status: "success";
  data: Record<string, unknown>[];
  affected_rows: number;
  refreshed_data?: {
    question: string;
    sql: string;
    data: Record<string, unknown>[];
    columns: string[];
    chart_type: string;
  };
}

export const adminApi = {
  ask: (question: string, user_id: string, session_id: string, model_provider: ModelProvider = "groq") =>
    request<AdminAskResponse>("/api/admin/ask", { question, user_id, session_id, model_provider }),
  askCompare: (question: string, user_id: string, session_id: string) =>
    request<CompareResponse>("/api/admin/ask/compare", { question, user_id, session_id }),
  confirm: (token: string, user_id: string, session_id: string) =>
    request<AdminConfirmResponse>("/api/admin/confirm", { token, user_id, session_id }),
  getQueryLogs: (user_id: string) =>
    requestGet<{ logs: QueryLog[] }>("/api/admin/query-logs", { user_id }),
  executeQuery: (sql: string, user_id: string, session_id: string) =>
    request<{ status: "success"; operation: "read"; data: Record<string, unknown>[]; columns: string[]; execution_time_ms: number }>(
      "/api/admin/query",
      { sql, user_id, session_id }
    )
};

// ============ Pipeline routing evaluation (confusion matrix / precision / recall / F1) ============

export const evaluationApi = {
  getLatestPipelineEval: (user_id: string) =>
    requestGet<PipelineEvalRun>("/api/admin/pipeline-eval/latest", { user_id }),
  getLatestBenchmarkEval: (user_id: string) =>
    requestGet<BenchmarkEvalRun>("/api/admin/benchmark-eval/latest", { user_id }),
  getBenchmarkEvalHistory: (user_id: string) =>
    requestGet<{ history: any[] }>("/api/admin/benchmark-eval/history", { user_id }),
  getBenchmarkQuestions: (user_id: string) =>
    requestGet<{ questions: BenchmarkQuestionApi[] }>("/api/admin/benchmark-questions", { user_id }),
  addBenchmarkQuestion: (user_id: string, question: string, gold_sql: string, gold_answer: string) =>
    request<BenchmarkQuestionApi>("/api/admin/benchmark-questions", { user_id, question, gold_sql, gold_answer }),
  runBenchmark: (user_id: string, limit?: number) =>
    request<{ status: "started"; message: string }>("/api/admin/benchmark-eval/run", { user_id, limit }),
  getBenchmarkRunStatus: (user_id: string) =>
    requestGet<{ is_running: boolean; error: string | null }>("/api/admin/benchmark-eval/status", { user_id })
};

export interface BenchmarkQuestionApi {
  id: string;
  question: string;
  gold_sql: string;
  gold_answer: string | null;
  category: string;
  created_at: string;
}

// ============ Analytics (real query success rate / execution metrics / error rate) ============

export interface AnalyticsSummary {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  success_rate: number;
  error_rate: number;
  avg_execution_time_ms: number;
  status_breakdown: { status: string; count: number }[];
  token_usage_available: false;
}

export const analyticsApi = {
  getSummary: (user_id: string) =>
    requestGet<AnalyticsSummary>("/api/admin/analytics/summary", { user_id })
};

// ============ Saved Observation Notes (Supabase Persisted) ============

export interface NoteApi {
  id: string;
  title: string;
  content: string;
  sessionId: string;
  lastModified: number;
}

export const notesApi = {
  list: (user_id: string) =>
    requestGet<{ notes: NoteApi[] }>("/api/user/notes", { user_id }),
  save: (user_id: string, note: NoteApi) =>
    request<{ status: string; note_id: string }>("/api/user/notes", {
      user_id,
      id: note.id,
      title: note.title,
      content: note.content,
      session_id: note.sessionId,
      last_modified: note.lastModified
    }),
  delete: (user_id: string, note_id: string) =>
    request<{ status: string; message: string }>(`/api/user/notes/${note_id}`, { user_id }, "DELETE")
};
