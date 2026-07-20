import { create } from "zustand";
import type { Message, ModelProvider } from "../types";
import { userApi, ApiError, type CompareResponse } from "../lib/apiClient";
import { useAuthStore } from "./authStore";
import { useUiStore } from "./uiStore";
import { mapChartRecommendation, SUPPORTED_CHART_TYPES } from "../lib/chartMapping";
import { useSessionStore } from "./sessionStore";

interface ChatState {
  messagesBySession: Record<string, Message[]>;
  isLoading: boolean;
  getMessages: (sessionId: string) => Message[];
  addMessage: (sessionId: string, sender: "user" | "ai", text: string) => Promise<void>;
  clearSessionMessages: (sessionId: string) => void;
  submitUserQuery: (sessionId: string, queryText: string) => Promise<void>;
  submitClarificationAnswer: (sessionId: string, chosenOption: string) => Promise<void>;
  compareQuestion: (sessionId: string, questionText: string) => Promise<CompareResponse | null>;
  initializeChat: () => void;
  fetchSessionMessages: (sessionId: string) => Promise<void>;
}

function appendMessage(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  sessionId: string,
  message: Message
) {
  set((state) => {
    const currentList = state.messagesBySession[sessionId] || [];
    const updated = {
      ...state.messagesBySession,
      [sessionId]: [...currentList, message]
    };
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_chat_messages_${userId}` : "user_chat_messages";
    localStorage.setItem(storageKey, JSON.stringify(updated));
    return {
      messagesBySession: updated
    };
  });
}

function autoRenameSessionIfNeeded(sessionId: string, text: string) {
  try {
    const sessionStore = useSessionStore.getState();
    const currentSession = sessionStore.sessions.find(s => s.id === sessionId);
    if (
      currentSession &&
      (currentSession.title.startsWith("Analytical Chat") ||
        currentSession.title.startsWith("New Chat"))
    ) {
      let autoTitle = text.trim();
      autoTitle = autoTitle.replace(/^(what is|show me|how many|show|list|get|find|can you tell me|tampilkan|hitung|apakah|bagaimana|siapa)\s+/i, "");
      autoTitle = autoTitle.replace(/\?+$/, "");
      if (autoTitle.length > 200) {
        autoTitle = autoTitle.substring(0, 197) + "...";
      }
      autoTitle = autoTitle.charAt(0).toUpperCase() + autoTitle.slice(1);
      
      if (autoTitle) {
        sessionStore.renameSession(sessionId, autoTitle);
      }
    }
  } catch (e) {
    console.error("Auto rename failed:", e);
  }
}

async function askBackend(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  sessionId: string,
  question: string,
  displayText: string
) {
  const userId = useAuthStore.getState().user?.userId;
  const provider: ModelProvider = useUiStore.getState().modelProvider;

  appendMessage(set, sessionId, {
    id: `msg-${Date.now()}-user`,
    sender: "user",
    text: displayText,
    timestamp: Date.now()
  });
  set(() => ({ isLoading: true }));

  if (!userId) {
    appendMessage(set, sessionId, {
      id: `msg-${Date.now()}-ai`,
      sender: "ai",
      text: "You're not logged in. Please sign in again.",
      timestamp: Date.now(),
      status: "Blocked"
    });
    set(() => ({ isLoading: false }));
    return;
  }

  try {
    const res = await userApi.ask(question, userId, sessionId, provider);

    const aiMessage: Message =
      res.status === "clarification_needed"
        ? {
            id: `msg-${Date.now()}-ai`,
            sender: "ai",
            text: res.explanation,
            timestamp: Date.now(),
            status: "Success",
            isClarification: true,
            clarificationOptions: res.options,
            provider: res.model_provider,
            modelName: res.model_name
          }
        : {
            id: `msg-${Date.now()}-ai`,
            sender: "ai",
            text: res.explanation,
            timestamp: Date.now(),
            status: "Success",
            sql: res.generated_sql,
            executionTimeMs: res.metadata?.query_execution_time_ms,
            rowCount: res.data.length,
            resultPreview: res.data.length > 0 ? { columns: res.columns, rows: res.data } : undefined,
            chartData: mapChartRecommendation(
              (res.chart_recommendation as { type?: string })?.type,
              res.data,
              res.columns,
              SUPPORTED_CHART_TYPES
            ),
            provider: res.model_provider,
            modelName: res.model_name
          };

    appendMessage(set, sessionId, aiMessage);
  } catch (e) {
    const message = e instanceof ApiError ? e.message : "Something went wrong. Please try again.";
    const msgLower = message.toLowerCase();
    const isBlocked =
      e instanceof ApiError &&
      e.status === 422 &&
      (msgLower.includes("not allowed") ||
       msgLower.includes("only read operations") ||
       msgLower.includes("data insertion") ||
       msgLower.includes("data modification") ||
       msgLower.includes("data deletion") ||
       msgLower.includes("not authorized") ||
       msgLower.includes("permission denied") ||
       msgLower.includes("sql validation failed"));

    appendMessage(set, sessionId, {
      id: `msg-${Date.now()}-ai`,
      sender: "ai",
      text: isBlocked
        ? `I can help analyze the data, but this chat is read-only. I cannot add, edit, or delete database records. (${message})`
        : message,
      timestamp: Date.now(),
      status: isBlocked ? "Blocked" : undefined
    });
  } finally {
    set(() => ({ isLoading: false }));
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  messagesBySession: {},
  isLoading: false,

  getMessages: (sessionId) => {
    return get().messagesBySession[sessionId] || [];
  },

  addMessage: async (sessionId, sender, text) => {
    appendMessage(set, sessionId, {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      sender,
      text,
      timestamp: Date.now(),
      status: "Success"
    });
  },

  clearSessionMessages: (sessionId) => {
    set((state) => {
      const updated = { ...state.messagesBySession };
      delete updated[sessionId];
      const userId = useAuthStore.getState().user?.userId;
      const storageKey = userId ? `user_chat_messages_${userId}` : "user_chat_messages";
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { messagesBySession: updated };
    });
  },

  submitUserQuery: async (sessionId, queryText) => {
    autoRenameSessionIfNeeded(sessionId, queryText);
    await askBackend(set, sessionId, queryText, queryText);
  },

  submitClarificationAnswer: async (sessionId, chosenOption) => {
    autoRenameSessionIfNeeded(sessionId, chosenOption);
    await askBackend(set, sessionId, chosenOption, chosenOption);
  },

  compareQuestion: async (sessionId, questionText) => {
    const userId = useAuthStore.getState().user?.userId;
    if (!userId) return null;

    return userApi.askCompare(questionText, userId, sessionId);
  },

  initializeChat: () => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_chat_messages_${userId}` : "user_chat_messages";
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        set({ messagesBySession: JSON.parse(saved) });
      } catch (e) {
        console.error("Failed to parse saved chat messages", e);
      }
    } else {
      set({ messagesBySession: {} });
    }
  },

  fetchSessionMessages: async (sessionId) => {
    const userId = useAuthStore.getState().user?.userId;
    if (!userId || !sessionId) return;

    try {
      const res = await userApi.getSessionMessages(userId, sessionId);
      if (res.messages) {
        set((state) => {
          const updated = {
            ...state.messagesBySession,
            [sessionId]: res.messages
          };
          const storageKey = `user_chat_messages_${userId}`;
          localStorage.setItem(storageKey, JSON.stringify(updated));
          return { messagesBySession: updated };
        });
      }
    } catch (e) {
      console.error("Failed to load messages from db for session:", sessionId, e);
    }
  }
}));
