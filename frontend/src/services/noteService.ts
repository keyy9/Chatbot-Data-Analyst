import { useNoteStore } from "../store/noteStore";

export const noteService = {
  create: (title: string, content: string, sessionId: string) => {
    useNoteStore.getState().createNote(title, content, sessionId);
  },
  update: (id: string, title: string, content: string, sessionId: string) => {
    useNoteStore.getState().updateNote(id, title, content, sessionId);
  },
  delete: (id: string) => {
    return useNoteStore.getState().deleteNote(id);
  },
  getAll: () => {
    return useNoteStore.getState().notes;
  }
};
