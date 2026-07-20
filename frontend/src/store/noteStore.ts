import { create } from "zustand";
import type { Note } from "../types";
import { notesApi, ApiError } from "../lib/apiClient";
import { useAuthStore } from "./authStore";

interface NoteState {
  notes: Note[];
  selectedNoteId: string | null;
  createNote: (title: string, content: string, sessionId: string) => void;
  updateNote: (id: string, title: string, content: string, sessionId: string) => void;
  deleteNote: (id: string) => Promise<void>;
  setSelectedNoteId: (id: string | null) => void;
  initializeNotes: () => void;
}

export const useNoteStore = create<NoteState>((set) => ({
  notes: [],
  selectedNoteId: null,

  createNote: (title, content, sessionId) => {
    const newNote: Note = {
      id: `note-${Date.now()}`,
      title: title || "Untitled Note",
      content,
      sessionId,
      lastModified: Date.now()
    };

    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_notes_${userId}` : "user_notes";

    set((state) => {
      const updated = [newNote, ...state.notes];
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { notes: updated, selectedNoteId: newNote.id };
    });

    if (userId) {
      notesApi.save(userId, newNote).catch((e) => console.error("Failed to save note to db:", e));
    }
  },

  updateNote: (id, title, content, sessionId) => {
    const updatedNote: Note = {
      id,
      title: title || "Untitled Note",
      content,
      sessionId,
      lastModified: Date.now()
    };

    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_notes_${userId}` : "user_notes";

    set((state) => {
      const updated = state.notes.map((n) => (n.id === id ? updatedNote : n));
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { notes: updated };
    });

    if (userId) {
      notesApi.save(userId, updatedNote).catch((e) => console.error("Failed to update note in db:", e));
    }
  },

  deleteNote: async (id) => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_notes_${userId}` : "user_notes";

    const commitLocalDelete = () => {
      set((state) => {
        const filtered = state.notes.filter((n) => n.id !== id);
        localStorage.setItem(storageKey, JSON.stringify(filtered));
        let nextSelected = state.selectedNoteId;
        if (state.selectedNoteId === id) {
          nextSelected = filtered.length > 0 ? filtered[0].id : null;
        }
        return { notes: filtered, selectedNoteId: nextSelected };
      });
    };

    if (!userId) {
      commitLocalDelete();
      return;
    }

    try {
      await notesApi.delete(userId, id);
      commitLocalDelete();
    } catch (e) {
      // A 404 means the note isn't in the DB (local-only, never synced), so
      // deleting it locally is safe - it can't resurrect from a row that
      // doesn't exist. Only a real network/server error should block it.
      if (e instanceof ApiError && e.status === 404) {
        commitLocalDelete();
        return;
      }
      console.error("Failed to delete note from db, keeping it locally:", e);
      throw e;
    }
  },

  setSelectedNoteId: (id) => {
    set({ selectedNoteId: id });
  },

  initializeNotes: () => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_notes_${userId}` : "user_notes";
    if (userId) {
      notesApi
        .list(userId)
        .then((res) => {
          if (res.notes && res.notes.length > 0) {
            set({ notes: res.notes, selectedNoteId: res.notes[0].id });
            localStorage.setItem(storageKey, JSON.stringify(res.notes));
            return;
          }

          // DB is empty: this could genuinely mean "no notes" (including
          // "user deleted them all"), so it must NOT be treated as license
          // to resurrect a stale local cache. Only migrate pre-existing
          // local-only notes into the DB once, ever, per user.
          const migrationKey = `notes_migrated_${userId}`;
          const alreadyMigrated = localStorage.getItem(migrationKey);
          const saved = localStorage.getItem(storageKey);

          if (!alreadyMigrated && saved) {
            const parsed = JSON.parse(saved);
            if (parsed.length > 0) {
              set({ notes: parsed, selectedNoteId: parsed[0].id });
              parsed.forEach((note: any) => {
                notesApi.save(userId, note).catch((e) => console.error("Failed to migrate note to db:", e));
              });
              localStorage.setItem(migrationKey, "1");
              return;
            }
          }

          localStorage.setItem(migrationKey, "1");
          set({ notes: [], selectedNoteId: null });
          localStorage.setItem(storageKey, JSON.stringify([]));
        })
        .catch((e) => {
          console.error("Failed to load notes from db:", e);
          const saved = localStorage.getItem(storageKey);
          if (saved) {
            set({ notes: JSON.parse(saved) });
          } else {
            set({ notes: [], selectedNoteId: null });
          }
        });
      return;
    }

    const saved = localStorage.getItem(storageKey);
    if (saved) {
      set({ notes: JSON.parse(saved) });
    } else {
      // Mock initial note
      const mockNote: Note = {
        id: "note-init",
        title: "Welcome Note",
        content: "Use this panel to save summaries, key observations, or queries you run frequently. You can also link notes directly to active chat sessions.",
        sessionId: "",
        lastModified: Date.now()
      };
      set({ notes: [mockNote] });
      localStorage.setItem(storageKey, JSON.stringify([mockNote]));
    }
  }
}));
