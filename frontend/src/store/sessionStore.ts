import { create } from "zustand";
import type { ChatSession } from "../types";
import { userApi, ApiError } from "../lib/apiClient";
import { useAuthStore } from "./authStore";

interface SessionState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  searchQuery: string;
  createSession: (title?: string) => string;
  deleteSession: (id: string) => Promise<void>;
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
      while (existingTitles.has(`new chat ${counter}`)) {
        counter++;
      }
      finalTitle = `New Chat ${counter}`;
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

    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_chat_sessions_${userId}` : "user_chat_sessions";

    set((state) => {
      const updated = [newSess, ...state.sessions];
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { sessions: updated, activeSessionId: newSessionId };
    });

    if (userId) {
      userApi.createSession(userId, newSessionId, finalTitle).catch((e) => console.error("Failed to save session to db:", e));
    }

    return newSessionId;
  },

  deleteSession: async (id) => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_chat_sessions_${userId}` : "user_chat_sessions";

    const commitLocalDelete = () => {
      set((state) => {
        const filtered = state.sessions.filter((s) => s.id !== id);
        localStorage.setItem(storageKey, JSON.stringify(filtered));
        let nextActive = state.activeSessionId;
        if (state.activeSessionId === id) {
          nextActive = filtered.length > 0 ? filtered[0].id : null;
        }
        return { sessions: filtered, activeSessionId: nextActive };
      });
    };

    if (!userId) {
      commitLocalDelete();
      return;
    }

    try {
      await userApi.deleteSession(userId, id);
      commitLocalDelete();
    } catch (e) {
      // A 404 means the session isn't in the DB (local-only, never synced),
      // so deleting it locally is safe - it can't resurrect from a row that
      // doesn't exist. Only a real network/server error should block the
      // delete, since then the DB might still hold it and re-hydrate it.
      if (e instanceof ApiError && e.status === 404) {
        commitLocalDelete();
        return;
      }
      console.error("Failed to delete session from db, keeping it locally:", e);
      throw e;
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

    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_chat_sessions_${userId}` : "user_chat_sessions";

    set((state) => {
      const updated = state.sessions.map((s) =>
        s.id === id ? { ...s, title: finalTitle } : s
      );
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { sessions: updated };
    });

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
    const storageKey = userId ? `user_chat_sessions_${userId}` : "user_chat_sessions";
    if (userId) {
      userApi.getSessions(userId)
        .then((res) => {
          if (res.sessions && res.sessions.length > 0) {
            set({
              sessions: res.sessions,
              activeSessionId: get().activeSessionId || res.sessions[0].id
            });
            localStorage.setItem(storageKey, JSON.stringify(res.sessions));
            return;
          }

          // DB has no sessions: could genuinely mean "user deleted them
          // all", so don't treat that as license to resurrect a stale
          // local cache. Only migrate pre-existing local-only sessions
          // into the DB once, ever, per user.
          const migrationKey = `sessions_migrated_${userId}`;
          const alreadyMigrated = localStorage.getItem(migrationKey);
          const saved = localStorage.getItem(storageKey);

          if (!alreadyMigrated && saved) {
            const parsed = JSON.parse(saved);
            if (parsed.length > 0) {
              set({ sessions: parsed, activeSessionId: parsed.length > 0 ? parsed[0].id : null });
              parsed.forEach((sess: ChatSession) => {
                userApi.createSession(userId, sess.id, sess.title).catch((e) => console.error("Failed to migrate session to db:", e));
              });
              localStorage.setItem(migrationKey, "1");
              return;
            }
          }

          localStorage.setItem(migrationKey, "1");

          // Create initial welcome session in db if truly empty
          const initialSessId = crypto.randomUUID();
          const initialSess: ChatSession = {
            id: initialSessId,
            title: "Retail Sales Overview",
            createdAt: Date.now()
          };
          set({ sessions: [initialSess], activeSessionId: initialSessId });
          localStorage.setItem(storageKey, JSON.stringify([initialSess]));
          userApi.createSession(userId, initialSessId, "Retail Sales Overview").catch((err) => console.error("Failed to create default session:", err));
        })
        .catch((e) => {
          console.error("Failed to load sessions from db:", e);
          const saved = localStorage.getItem(storageKey);
          if (saved) {
            try {
              const parsed = JSON.parse(saved).filter((s: any) => s && typeof s.id === "string" && !s.id.startsWith("sess-"));
              set({ sessions: parsed, activeSessionId: parsed.length > 0 ? parsed[0].id : null });
            } catch (err) {
              console.error("Failed to parse sessions from local storage:", err);
            }
          }
        });
      return;
    }

    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed: ChatSession[] = JSON.parse(saved).filter((s: any) => s && typeof s.id === "string" && !s.id.startsWith("sess-"));
        set({
          sessions: parsed,
          activeSessionId: parsed.length > 0 ? parsed[0].id : null
        });
      } catch (err) {
        console.error("Failed to parse sessions from local storage:", err);
      }
    } else {
      // Create initial welcome session
      const initialSessId = crypto.randomUUID();
      const initialSess: ChatSession = {
        id: initialSessId,
        title: "Retail Sales Overview",
        createdAt: Date.now()
      };
      set({ sessions: [initialSess], activeSessionId: initialSessId });
      localStorage.setItem(storageKey, JSON.stringify([initialSess]));
    }
  }
}));
