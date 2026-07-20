import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { MessageSquare, Edit2, Trash2, Check, X } from "lucide-react";
import { useSessionStore } from "../../store/sessionStore";
import { useChatStore } from "../../store/chatStore";

export const SessionList: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    sessions,
    activeSessionId,
    searchQuery,
    setActiveSessionId,
    renameSession,
    deleteSession,
  } = useSessionStore();
  const { clearSessionMessages } = useChatStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleStartRename = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const handleSaveRename = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      renameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDeleteSessionClick = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this chat session? All its messages will be cleared.")) {
      deleteSession(id);
      clearSessionMessages(id);
    }
  };

  return (
    <div className="space-y-1 py-1 font-sans">
      {filteredSessions.length === 0 ? (
        <p className="text-[10px] text-text-faint dark:text-text-faint text-center py-4">
          No sessions found
        </p>
      ) : (
        filteredSessions.map((session) => {
          const isActive = session.id === activeSessionId;
          const isEditing = session.id === editingId;

          return (
            <div
              key={session.id}
              onClick={() => {
                if (!isEditing) {
                  setActiveSessionId(session.id);
                  if (location.pathname !== "/chat") {
                    navigate("/chat");
                  }
                }
              }}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl text-sm transition-all cursor-pointer border ${
                isActive
                  ? "bg-slate-200 dark:bg-surface-hover text-slate-900 dark:text-white border-slate-300 dark:border-border"
                  : "bg-transparent text-slate-600 dark:text-text-muted border-transparent hover:bg-slate-100 dark:hover:bg-surface-hover/30"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-text-muted dark:text-text-faint" />
                {isEditing ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full bg-white dark:bg-surface border border-slate-300 dark:border-border text-black dark:text-white px-1 py-0.5 rounded focus:outline-none font-bold text-sm"
                    autoFocus
                  />
                ) : (
                  <span className="truncate font-semibold text-left">{session.title}</span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1 flex-shrink-0 ml-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                {isEditing ? (
                  <>
                    <button
                      onClick={(e) => handleSaveRename(session.id, e)}
                      className="p-0.5 text-success hover:text-success transition-colors cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={handleCancelRename}
                      className="p-0.5 text-red-500 hover:text-red-400 transition-colors cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={(e) => handleStartRename(session.id, session.title, e)}
                      className="p-0.5 hover:text-slate-800 dark:hover:text-white transition-colors cursor-pointer"
                      title="Rename Session"
                    >
                      <Edit2 className="w-3 h-3 text-text-muted" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteSessionClick(session.id, e)}
                      className="p-0.5 hover:text-red-500 transition-colors cursor-pointer"
                      title="Delete Session"
                    >
                      <Trash2 className="w-3 h-3 text-text-muted" />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};
