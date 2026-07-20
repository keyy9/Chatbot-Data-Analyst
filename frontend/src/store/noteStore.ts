import { create } from "zustand";
import type { Note } from "../types";

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
  },

  updateNote: (id, title, content, sessionId) => {
    set((state) => {
      const updated = state.notes.map((n) =>
        n.id === id
          ? { ...n, title: title || "Untitled Note", content, sessionId, lastModified: Date.now() }
          : n
      );
      localStorage.setItem("user_notes", JSON.stringify(updated));
      return { notes: updated };
    });
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
  },

  setSelectedNoteId: (id) => {
    set({ selectedNoteId: id });
  },

  initializeNotes: () => {
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
