import { create } from "zustand";
import type { Note } from "../types";
import { notesApi, ApiError } from "../lib/apiClient";
import { useAuthStore } from "./authStore";

interface NoteState {
  notes: Note[];
  selectedNoteId: string | null;
  createNote: (title: string, content: string, sessionId: string, category?: string) => string;
  updateNote: (id: string, title: string, content: string, sessionId: string, category?: string, isPinned?: boolean) => void;
  togglePinNote: (id: string) => void;
  deleteNote: (id: string) => Promise<void>;
  setSelectedNoteId: (id: string | null) => void;
  initializeNotes: () => void;
}

export const useNoteStore = create<NoteState>((set, get) => ({
  notes: [],
  selectedNoteId: null,

  createNote: (title, content, sessionId, category = "General") => {
    const newNote: Note = {
      id: `note-${Date.now()}`,
      title: title || "Untitled Observation",
      content,
      sessionId,
      category,
      isPinned: false,
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
    return newNote.id;
  },

  updateNote: (id, title, content, sessionId, category, isPinned) => {
    const existing = get().notes.find((n) => n.id === id);
    const updatedNote: Note = {
      id,
      title: title || "Untitled Observation",
      content,
      sessionId,
      category: category ?? existing?.category ?? "General",
      isPinned: isPinned ?? existing?.isPinned ?? false,
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

  togglePinNote: (id) => {
    const note = get().notes.find((n) => n.id === id);
    if (!note) return;
    get().updateNote(id, note.title, note.content, note.sessionId, note.category, !note.isPinned);
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

    // No signed-in user yet: show whatever was cached locally, never a
    // seeded placeholder note the user never wrote.
    const saved = localStorage.getItem(storageKey);
    set({ notes: saved ? JSON.parse(saved) : [], selectedNoteId: null });
  }
}));
