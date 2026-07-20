import { create } from "zustand";
import type { ChatSession } from "../types";

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
  },

  renameSession: (id, newTitle) => {
    set((state) => {
      let finalTitle = newTitle.trim();
      let counter = 1;
      let checkTitle = finalTitle;
      const existingTitles = new Set(
        state.sessions.filter(s => s.id !== id).map(s => s.title.trim().toLowerCase())
      );
      while (existingTitles.has(checkTitle.toLowerCase())) {
        checkTitle = `${finalTitle} (${counter})`;
        counter++;
      }
      finalTitle = checkTitle;

      const updated = state.sessions.map((s) =>
        s.id === id ? { ...s, title: finalTitle } : s
      );
      localStorage.setItem("user_chat_sessions", JSON.stringify(updated));
      return { sessions: updated };
    });
  },

  setActiveSessionId: (id) => {
    set({ activeSessionId: id });
  },

  setSearchQuery: (query) => {
    set({ searchQuery: query });
  },

  initializeSessions: () => {
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
