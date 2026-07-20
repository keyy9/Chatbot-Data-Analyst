import { create } from "zustand";
import type { ChatSession } from "../types";
import { userApi } from "../lib/apiClient";
import { useAuthStore } from "./authStore";

interface SessionState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  searchQuery: string;
  createSession: (title?: string) => string;
  deleteSession: (id: string) => void;
  renameSession: (id: string, newTitle: string) => void;
  setActiveSessionId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  initializeSessions: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  searchQuery: "",

  createSession: (title) => {
    const newSessionId = crypto.randomUUID();
    let finalTitle = title;
    if (!finalTitle) {
      let counter = 1;
      const existingTitles = new Set(get().sessions.map(s => s.title.trim().toLowerCase()));
      while (existingTitles.has(`analytical chat ${counter}`)) {
        counter++;
      }
      finalTitle = `Analytical Chat ${counter}`;
    } else {
      let counter = 1;
      let checkTitle = finalTitle.trim();
      const existingTitles = new Set(get().sessions.map(s => s.title.trim().toLowerCase()));
      while (existingTitles.has(checkTitle.toLowerCase())) {
        checkTitle = `${finalTitle.trim()} (${counter})`;
        counter++;
      }
      finalTitle = checkTitle;
    }
    const newSess: ChatSession = {
      id: newSessionId,
      title: finalTitle,
      createdAt: Date.now()
    };

    set((state) => {
      const updated = [newSess, ...state.sessions];
      localStorage.setItem("user_chat_sessions", JSON.stringify(updated));
      return { sessions: updated, activeSessionId: newSessionId };
    });

    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      userApi.createSession(userId, newSessionId, finalTitle).catch((e) => console.error("Failed to save session to db:", e));
    }

    return newSessionId;
  },

  deleteSession: (id) => {
    set((state) => {
      const filtered = state.sessions.filter((s) => s.id !== id);
      localStorage.setItem("user_chat_sessions", JSON.stringify(filtered));
      let nextActive = state.activeSessionId;
      if (state.activeSessionId === id) {
        nextActive = filtered.length > 0 ? filtered[0].id : null;
      }
      return { sessions: filtered, activeSessionId: nextActive };
    });

    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      userApi.deleteSession(userId, id).catch((e) => console.error("Failed to delete session from db:", e));
    }
  },

  renameSession: (id, newTitle) => {
    let finalTitle = newTitle.trim();
    let counter = 1;
    let checkTitle = finalTitle;
    const existingTitles = new Set(
      get().sessions.filter(s => s.id !== id).map(s => s.title.trim().toLowerCase())
    );
    while (existingTitles.has(checkTitle.toLowerCase())) {
      checkTitle = `${finalTitle} (${counter})`;
      counter++;
    }
    finalTitle = checkTitle;

    set((state) => {
      const updated = state.sessions.map((s) =>
        s.id === id ? { ...s, title: finalTitle } : s
      );
      localStorage.setItem("user_chat_sessions", JSON.stringify(updated));
      return { sessions: updated };
    });

    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      userApi.renameSession(userId, id, finalTitle).catch((e) => console.error("Failed to rename session in db:", e));
    }
  },

  setActiveSessionId: (id) => {
    set({ activeSessionId: id });
  },

  setSearchQuery: (query) => {
    set({ searchQuery: query });
  },

  initializeSessions: () => {
    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      userApi.getSessions(userId)
        .then((res) => {
          if (res.sessions && res.sessions.length > 0) {
            set({
              sessions: res.sessions,
              activeSessionId: get().activeSessionId || res.sessions[0].id
            });
            localStorage.setItem("user_chat_sessions", JSON.stringify(res.sessions));
          } else {
            // Fallback if db has no sessions but local storage has them
            const saved = localStorage.getItem("user_chat_sessions");
            if (saved) {
              const parsed = JSON.parse(saved);
              set({ sessions: parsed, activeSessionId: parsed.length > 0 ? parsed[0].id : null });
              
              // Upload them to DB!
              parsed.forEach((sess: ChatSession) => {
                userApi.createSession(userId, sess.id, sess.title).catch((e) => console.error("Failed to sync session to db on init:", e));
              });
            } else {
              // Create initial welcome session in db if empty
              const initialSessId = crypto.randomUUID();
              const initialSess: ChatSession = {
                id: initialSessId,
                title: "Retail Sales Overview",
                createdAt: Date.now()
              };
              set({ sessions: [initialSess], activeSessionId: initialSessId });
              localStorage.setItem("user_chat_sessions", JSON.stringify([initialSess]));
              userApi.createSession(userId, initialSessId, "Retail Sales Overview").catch((err) => console.error("Failed to create default session:", err));
            }
          }
        })
        .catch((e) => {
          console.error("Failed to load sessions from db:", e);
          const saved = localStorage.getItem("user_chat_sessions");
          if (saved) {
            const parsed = JSON.parse(saved);
            set({ sessions: parsed, activeSessionId: parsed.length > 0 ? parsed[0].id : null });
          }
        });
      return;
    }

    const saved = localStorage.getItem("user_chat_sessions");
    if (saved) {
      const parsed: ChatSession[] = JSON.parse(saved);
      set({
        sessions: parsed,
        activeSessionId: parsed.length > 0 ? parsed[0].id : null
      });
    } else {
      // Create initial welcome session
      const initialSessId = `sess-${Date.now()}`;
      const initialSess: ChatSession = {
        id: initialSessId,
        title: "Retail Sales Overview",
        createdAt: Date.now()
      };
      set({ sessions: [initialSess], activeSessionId: initialSessId });
      localStorage.setItem("user_chat_sessions", JSON.stringify([initialSess]));
    }
  }
}));
