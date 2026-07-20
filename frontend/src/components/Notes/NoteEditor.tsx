import React, { useState, useEffect } from "react";
import { ArrowLeft, Trash2, Save, Link } from "lucide-react";
import { useNoteStore } from "../../store/noteStore";
import { useSessionStore } from "../../store/sessionStore";

interface NoteEditorProps {
  onClose: () => void;
}

export const NoteEditor: React.FC<NoteEditorProps> = ({ onClose }) => {
  const { selectedNoteId, notes, updateNote, deleteNote } = useNoteStore();
  const { sessions } = useSessionStore();

  const note = notes.find((n) => n.id === selectedNoteId);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [bindSessionId, setBindSessionId] = useState("");

  useEffect(() => {
    if (note) {
      setTitle(note.title);
      setContent(note.content);
      setBindSessionId(note.sessionId);
    }
  }, [note]);

  if (!note) return null;

  const handleSave = () => {
    updateNote(note.id, title, content, bindSessionId);
    onClose();
  };

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this observation?")) {
      try {
        await deleteNote(note.id);
        onClose();
      } catch {
        alert("Failed to delete this observation. Please try again.");
      }
    }
  };

  return (
    <div className="space-y-4 text-left font-sans animate-fade-in text-slate-800 dark:text-text">
      {/* Top action bar */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-border/60">
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-xs text-text-faint hover:text-slate-700 dark:hover:text-white transition-all cursor-pointer font-bold"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back List
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDelete}
            className="p-1.5 text-red-500 hover:text-danger hover:bg-red-500/10 rounded-lg transition-all cursor-pointer"
            title="Delete note"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 bg-gradient-to-r from-accent to-teal hover:opacity-90 text-white rounded-lg flex items-center gap-1.5 text-xs font-bold shadow-sm cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" />
            Save Note
          </button>
        </div>
      </div>

      {/* Title */}
      <div className="space-y-1">
        <label className="text-[10px] font-bold text-text-faint uppercase font-mono">Note Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Sales analysis observation"
          className="w-full text-xs font-bold p-2.5 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-text dark:text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:outline-none"
        />
      </div>

      {/* Link Session */}
      <div className="space-y-1">
        <label className="text-[10px] font-bold text-text-faint uppercase font-mono flex items-center gap-1">
          <Link className="w-3.5 h-3.5 text-text-faint" />
          Link Chat Session
        </label>
        <select
          value={bindSessionId}
          onChange={(e) => setBindSessionId(e.target.value)}
          className="w-full text-xs p-2.5 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-slate-800 dark:text-text focus:ring-2 focus:ring-accent focus:outline-none cursor-pointer"
        >
          <option value="">-- No Linked Session --</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      <div className="space-y-1">
        <label className="text-[10px] font-bold text-text-faint uppercase font-mono">Content</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write down observations, summaries, queries notes, or next action items here..."
          className="w-full text-xs p-2.5 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-text dark:text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:outline-none"
          rows={10}
        />
      </div>
    </div>
  );
};
