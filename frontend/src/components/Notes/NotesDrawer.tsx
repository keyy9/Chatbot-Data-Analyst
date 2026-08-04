import React, { useState } from "react";
import { X, Plus, Search, FileText, Calendar, Bookmark, Pin, Trash2, Copy, Check } from "lucide-react";
import { useNoteStore } from "../../store/noteStore";
import { useSessionStore } from "../../store/sessionStore";
import { useUiStore } from "../../store/uiStore";
import { NoteEditor } from "./NoteEditor";

export const NotesDrawer: React.FC = () => {
  const { notesDrawerOpen, toggleNotesDrawer } = useUiStore();
  const { notes, createNote, selectedNoteId, setSelectedNoteId, togglePinNote, deleteNote } = useNoteStore();
  const { activeSessionId, sessions } = useSessionStore();
  const [search, setSearch] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!notesDrawerOpen) return null;

  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase()) ||
      (n.category && n.category.toLowerCase().includes(search.toLowerCase()))
  );

  // Sort pinned notes to top
  const sortedNotes = [...filteredNotes].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.lastModified - a.lastModified;
  });

  const activeNote = notes.find((n) => n.id === selectedNoteId);

  const handleAddNewNote = () => {
    const newId = createNote("New Analytical Observation", "", activeSessionId || "", "General");
    setSelectedNoteId(newId);
    setIsEditing(true);
  };

  const getSessionName = (id: string) => {
    const s = sessions.find((item) => item.id === id);
    return s ? s.title : "Workspace";
  };

  const handleCopyNote = (e: React.MouseEvent, noteId: string, content: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content);
    setCopiedId(noteId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDeleteCard = async (e: React.MouseEvent, noteId: string) => {
    e.stopPropagation();
    if (confirm("Delete this observation?")) {
      await deleteNote(noteId);
    }
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
        <div className="flex-1 flex flex-col min-h-0">
          {/* Header */}
          <div className="h-16 px-6 border-b border-slate-200 dark:border-border flex items-center justify-between bg-slate-50 dark:bg-surface-2/90 flex-shrink-0">
            <div>
              <h3 className="text-sm font-bold tracking-wide text-slate-800 dark:text-white flex items-center gap-2">
                <Bookmark className="w-4 h-4 text-accent fill-current" />
                Saved Observations
              </h3>
              <p className="text-[10px] text-text-faint dark:text-text-muted font-semibold mt-0.5">
                {notes.length} analytical findings saved in workspace
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleAddNewNote}
                className="p-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg flex items-center justify-center cursor-pointer shadow-sm transition-all active:scale-95"
                title="Add new observation note"
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
            <div className="p-6 overflow-y-auto flex-1">
              <NoteEditor onClose={() => setIsEditing(false)} />
            </div>
          ) : (
            /* Notes List Mode */
            <div className="p-6 space-y-4 flex-1 flex flex-col min-h-0">
              {/* Search */}
              <div className="relative flex-shrink-0">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search observations by title, content, tag..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border text-slate-800 dark:text-slate-100 placeholder:text-text-muted focus:ring-2 focus:ring-accent focus:border-accent pl-9 pr-4 py-2 rounded-lg text-xs focus:outline-none transition-all font-medium"
                />
              </div>

              {/* Notes Container */}
              <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                {sortedNotes.length === 0 ? (
                  <div className="p-12 text-center border border-dashed border-slate-200 dark:border-border rounded-xl text-text-muted">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50 text-accent" />
                    <p className="text-xs font-bold font-sans">No saved observations</p>
                    <p className="text-[10px] mt-1 text-text-faint">
                      Click <strong className="text-accent">"📌 Save Observation"</strong> on any AI response in chat to save it here!
                    </p>
                  </div>
                ) : (
                  sortedNotes.map((note) => (
                    <div
                      key={note.id}
                      onClick={() => {
                        setSelectedNoteId(note.id);
                        setIsEditing(true);
                      }}
                      className={`p-4 border rounded-xl transition-all cursor-pointer text-left space-y-2.5 group shadow-2xs relative ${
                        note.isPinned
                          ? "bg-accent/5 dark:bg-accent/10 border-accent/40"
                          : "bg-slate-50 hover:bg-slate-100 dark:bg-surface-2/45 dark:hover:bg-surface-hover/50 border-slate-200 dark:border-border"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-1.5 flex-1 min-w-0">
                          {note.isPinned && (
                            <Pin className="w-3.5 h-3.5 text-amber-500 fill-amber-500 flex-shrink-0" />
                          )}
                          <h4 className="text-xs font-bold text-text dark:text-text truncate group-hover:text-accent transition-colors">
                            {note.title}
                          </h4>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              togglePinNote(note.id);
                            }}
                            className={`p-1 rounded transition-colors ${
                              note.isPinned
                                ? "text-amber-500 hover:text-amber-600"
                                : "text-text-faint hover:text-amber-500 opacity-0 group-hover:opacity-100"
                            }`}
                            title={note.isPinned ? "Unpin observation" : "Pin observation to top"}
                          >
                            <Pin className="w-3 h-3" />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleCopyNote(e, note.id, note.content)}
                            className="p-1 text-text-faint hover:text-accent rounded opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Copy note content"
                          >
                            {copiedId === note.id ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteCard(e, note.id)}
                            className="p-1 text-text-faint hover:text-danger rounded opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Delete note"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>

                      <p className="text-[10px] text-text-faint dark:text-text-muted line-clamp-2 leading-relaxed">
                        {note.content || "Empty content... click to write observation."}
                      </p>

                      <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[9px] font-mono text-text-muted">
                        <span className="px-1.5 py-0.5 rounded bg-surface border border-border/80 text-accent font-bold">
                          {note.category || "Analytical Finding"}
                        </span>
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(note.lastModified).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-border bg-slate-50 dark:bg-surface-2/90 flex justify-end flex-shrink-0">
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
