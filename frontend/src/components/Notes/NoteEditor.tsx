import React, { useState, useEffect } from "react";
import { ArrowLeft, Trash2, Save, Link, Tag, Download, Copy, Check, Pin } from "lucide-react";
import { useNoteStore } from "../../store/noteStore";
import { useSessionStore } from "../../store/sessionStore";

interface NoteEditorProps {
  onClose: () => void;
}

const CATEGORIES = [
  "Analytical Finding",
  "Sales & Revenue",
  "Customer Insights",
  "Inventory & Orders",
  "Executive Summary",
  "General",
];

export const NoteEditor: React.FC<NoteEditorProps> = ({ onClose }) => {
  const { selectedNoteId, notes, updateNote, deleteNote, togglePinNote } = useNoteStore();
  const { sessions } = useSessionStore();

  const note = notes.find((n) => n.id === selectedNoteId);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [bindSessionId, setBindSessionId] = useState("");
  const [category, setCategory] = useState("General");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (note) {
      setTitle(note.title);
      setContent(note.content);
      setBindSessionId(note.sessionId);
      setCategory(note.category || "General");
    }
  }, [note]);

  if (!note) return null;

  const handleSave = () => {
    updateNote(note.id, title, content, bindSessionId, category, note.isPinned);
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

  const handleCopy = () => {
    const text = `# ${title}\nCategory: ${category}\n\n${content}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportMarkdown = () => {
    const text = `# ${title}\n*Category: ${category}*\n*Date: ${new Date(note.lastModified).toLocaleString()}*\n\n${content}`;
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-observation.md`;
    a.click();
    URL.revokeObjectURL(url);
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
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => togglePinNote(note.id)}
            className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
              note.isPinned
                ? "bg-amber-500/10 border-amber-500/30 text-amber-500"
                : "border-border text-text-faint hover:text-amber-500"
            }`}
            title={note.isPinned ? "Unpin note" : "Pin note to top"}
          >
            <Pin className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 border border-border text-text-faint hover:text-accent rounded-lg transition-all cursor-pointer"
            title="Copy Note Text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleExportMarkdown}
            className="p-1.5 border border-border text-text-faint hover:text-accent rounded-lg transition-all cursor-pointer"
            title="Export as Markdown (.md)"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1.5 text-red-500 hover:text-danger hover:bg-red-500/10 border border-transparent rounded-lg transition-all cursor-pointer"
            title="Delete note"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg flex items-center gap-1.5 text-xs font-bold shadow-xs cursor-pointer active:scale-95 transition-all"
          >
            <Save className="w-3.5 h-3.5" />
            Save
          </button>
        </div>
      </div>

      {/* Title */}
      <div className="space-y-1">
        <label className="text-[10px] font-bold text-text-faint uppercase font-mono">Observation Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Sales analysis observation"
          className="w-full text-xs font-bold p-2.5 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-text dark:text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:outline-none"
        />
      </div>

      {/* Category & Link Session Row */}
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <label className="text-[10px] font-bold text-text-faint uppercase font-mono flex items-center gap-1">
            <Tag className="w-3 h-3 text-text-faint" />
            Category Tag
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full text-xs p-2 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-slate-800 dark:text-text focus:ring-2 focus:ring-accent focus:outline-none cursor-pointer font-medium"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-[10px] font-bold text-text-faint uppercase font-mono flex items-center gap-1">
            <Link className="w-3 h-3 text-text-faint" />
            Chat Session
          </label>
          <select
            value={bindSessionId}
            onChange={(e) => setBindSessionId(e.target.value)}
            className="w-full text-xs p-2 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-slate-800 dark:text-text focus:ring-2 focus:ring-accent focus:outline-none cursor-pointer font-medium"
          >
            <option value="">-- Workspace --</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-1">
        <label className="text-[10px] font-bold text-text-faint uppercase font-mono">Observation Notes &amp; Findings</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write down observations, summaries, queries notes, or next action items here..."
          className="w-full text-xs p-3 bg-slate-50 dark:bg-surface-hover border border-slate-200 dark:border-border rounded-lg text-text dark:text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:outline-none font-mono leading-relaxed"
          rows={12}
        />
      </div>
    </div>
  );
};
