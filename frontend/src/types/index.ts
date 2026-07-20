export interface UserSession {
  userId: string;
  email: string;
  username?: string | null;
  role: "user" | "admin";
  isAuthenticated: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
}

export type ModelProvider = "groq" | "gemini";

export interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: number;
  status?: "Success" | "Blocked" | "Pending" | "Failed";
  sql?: string;
  executionTimeMs?: number;
  rowCount?: number;
  /** Operation status detail shown in a banner (e.g. "Query OK, 3 row(s) affected."). Admin write flow only. */
  message?: string;
  resultPreview?: {
    columns: string[];
    rows: Record<string, any>[];
  };
  chartData?: {
    type: "bar" | "line" | "pie" | "area";
    xAxisKey: string;
    dataKeys: string[];
    data: Record<string, any>[];
  };
  isClarification?: boolean;
  clarificationOptions?: string[];
  /** A generated write (INSERT/UPDATE/DELETE) awaiting explicit confirmation. Admin write flow only. */
  pendingConfirmation?: {
    token: string;
    operation: string;
    sqlPreview: string;
    expiresAt: string;
    resolved?: "confirmed" | "expired";
  };
  /** Which LLM answered this message (AI messages only). */
  provider?: ModelProvider;
  modelName?: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  sessionId: string; // link to chat session (optional or empty)
  lastModified: number;
}

export interface UserProfile {
  email: string;
  name: string;
  role: "User";
  createdAt: string;
  recentActivities: string[];
}
