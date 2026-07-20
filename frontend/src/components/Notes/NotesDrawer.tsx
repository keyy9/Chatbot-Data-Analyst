import React, { useState } from "react";
import { X, Plus, Search, FileText, Calendar } from "lucide-react";
import { useNoteStore } from "../../store/noteStore";
import { useSessionStore } from "../../store/sessionStore";
import { useUiStore } from "../../store/uiStore";
import { NoteEditor } from "./NoteEditor";

export const NotesDrawer: React.FC = () => {
  const { notesDrawerOpen, toggleNotesDrawer } = useUiStore();
  const { notes, createNote, selectedNoteId, setSelectedNoteId } = useNoteStore();
  const { activeSessionId, sessions } = useSessionStore();
  const [search, setSearch] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  if (!notesDrawerOpen) return null;

  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase())
  );

  const activeNote = notes.find((n) => n.id === selectedNoteId);

  const handleAddNewNote = () => {
    createNote("New Analytical Observation", "", activeSessionId || "");
    setIsEditing(true);
  };

  const getSessionName = (id: string) => {
    const s = sessions.find((item) => item.id === id);
    return s ? s.title : "Not Linked";
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end font-sans">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/40 backdrop-blur-xs transition-opacity duration-300 cursor-pointer"
        onClick={() => toggleNotesDrawer(false)}
      ></div>

      {/* Drawer Body */}
      <div className="relative w-full max-w-md bg-white dark:bg-surface border-l border-slate-200 dark:border-border h-screen flex flex-col justify-between shadow-2xl z-10 animate-slide-in text-slate-800 dark:text-text">
        <div>
          {/* Header */}
          <div className="h-16 px-6 border-b border-slate-200 dark:border-border flex items-center justify-between bg-slate-50 dark:bg-surface-2/90">
            <div>
              <h3 className="text-sm font-bold tracking-wide text-slate-800 dark:text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                Analytical Observations
              </h3>
              <p className="text-[10px] text-text-faint dark:text-text-muted font-semibold mt-0.5">
                Save queries summaries & details
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleAddNewNote}
                className="p-1.5 bg-gradient-to-r from-accent to-teal hover:opacity-90 text-white rounded-lg flex items-center justify-center cursor-pointer shadow-sm"
                title="Add observation"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => toggleNotesDrawer(false)}
                className="p-1.5 text-text-muted hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-surface-hover rounded-full transition-all cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Editor Mode Overlay */}
          {isEditing && activeNote ? (
            <div className="p-6">
              <NoteEditor onClose={() => setIsEditing(false)} />
            </div>
          ) : (
            /* Notes List Mode */
            <div className="p-6 space-y-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search observation notes..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border text-slate-800 dark:text-slate-100 placeholder:text-text-muted focus:ring-2 focus:ring-accent focus:border-accent pl-9 pr-4 py-2 rounded-lg text-xs focus:outline-none transition-all"
                />
              </div>

              {/* Notes Container */}
              <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-170px)] pr-1">
                {filteredNotes.length === 0 ? (
                  <div className="p-12 text-center border border-dashed border-slate-200 dark:border-border rounded-xl text-text-muted">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-xs font-bold font-sans">No observations saved</p>
                    <p className="text-[10px] mt-1">Click the + button to save your first data note.</p>
                  </div>
                ) : (
                  filteredNotes.map((note) => (
                    <div
                      key={note.id}
                      onClick={() => {
                        setSelectedNoteId(note.id);
                        setIsEditing(true);
                      }}
                      className="p-4 bg-slate-50 hover:bg-slate-100 dark:bg-surface-2/45 dark:hover:bg-surface-hover/50 border border-slate-200 dark:border-border rounded-xl transition-all cursor-pointer text-left space-y-2 group shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-text dark:text-text truncate pr-4 group-hover:text-accent transition-colors">
                          {note.title}
                        </h4>
                        <span className="text-[8px] px-1.5 py-0.5 bg-slate-200 dark:bg-[#1D3F3A] text-text-faint dark:text-text-muted rounded-full font-mono">
                          {getSessionName(note.sessionId)}
                        </span>
                      </div>
                      <p className="text-[10px] text-text-faint dark:text-text-muted line-clamp-2 leading-relaxed">
                        {note.content || "Empty content... click to write observation."}
                      </p>
                      <div className="flex items-center gap-1 text-[8px] text-text-muted font-mono pt-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(note.lastModified).toLocaleDateString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-border bg-slate-50 dark:bg-surface-2/90 flex justify-end">
          <button
            onClick={() => toggleNotesDrawer(false)}
            className="bg-slate-100 dark:bg-surface-hover hover:bg-surface-2 dark:hover:bg-[#1D3F3A] border border-border dark:border-border text-slate-700 dark:text-text-muted font-bold px-4 py-2 rounded-lg text-xs shadow-sm transition-all cursor-pointer font-sans"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
