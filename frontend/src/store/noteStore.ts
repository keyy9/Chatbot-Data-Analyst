import { create } from "zustand";
import type { Note } from "../types";
import { notesApi } from "../lib/apiClient";
import { useAuthStore } from "./authStore";

interface NoteState {
  notes: Note[];
  selectedNoteId: string | null;
  createNote: (title: string, content: string, sessionId: string) => void;
  updateNote: (id: string, title: string, content: string, sessionId: string) => void;
  deleteNote: (id: string) => void;
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

    set((state) => {
      const updated = [newNote, ...state.notes];
      localStorage.setItem("user_notes", JSON.stringify(updated));
      return { notes: updated, selectedNoteId: newNote.id };
    });

    const userId = useAuthStore.getState().user?.userId;
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

    set((state) => {
      const updated = state.notes.map((n) => (n.id === id ? updatedNote : n));
      localStorage.setItem("user_notes", JSON.stringify(updated));
      return { notes: updated };
    });

    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      notesApi.save(userId, updatedNote).catch((e) => console.error("Failed to update note in db:", e));
    }
  },

  deleteNote: (id) => {
    set((state) => {
      const filtered = state.notes.filter((n) => n.id !== id);
      localStorage.setItem("user_notes", JSON.stringify(filtered));
      let nextSelected = state.selectedNoteId;
      if (state.selectedNoteId === id) {
        nextSelected = filtered.length > 0 ? filtered[0].id : null;
      }
      return { notes: filtered, selectedNoteId: nextSelected };
    });

    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      notesApi.delete(userId, id).catch((e) => console.error("Failed to delete note from db:", e));
    }
  },

  setSelectedNoteId: (id) => {
    set({ selectedNoteId: id });
  },

  initializeNotes: () => {
    const userId = useAuthStore.getState().user?.userId;
    if (userId) {
      notesApi
        .list(userId)
        .then((res) => {
          if (res.notes && res.notes.length > 0) {
            set({ notes: res.notes, selectedNoteId: res.notes[0].id });
            localStorage.setItem("user_notes", JSON.stringify(res.notes));
          } else {
            // Fallback if db is empty
            const saved = localStorage.getItem("user_notes");
            if (saved) {
              const parsed = JSON.parse(saved);
              set({ notes: parsed, selectedNoteId: parsed.length > 0 ? parsed[0].id : null });
              // Automatically sync/upload local notes to the database
              parsed.forEach((note: any) => {
                notesApi.save(userId, note).catch((e) => console.error("Failed to sync note to db on init:", e));
              });
            }
          }
        })
        .catch((e) => {
          console.error("Failed to load notes from db:", e);
          const saved = localStorage.getItem("user_notes");
          if (saved) {
            set({ notes: JSON.parse(saved) });
          }
        });
      return;
    }

    const saved = localStorage.getItem("user_notes");
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
      localStorage.setItem("user_notes", JSON.stringify([mockNote]));
    }
  }
}));
