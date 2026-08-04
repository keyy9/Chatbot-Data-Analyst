import React, { useRef, useEffect } from "react";
import { Sparkles, Trash2, RefreshCw, Mic, Square, MicOff, Send, MessageSquarePlus, Plus, Edit2 } from "lucide-react";
import type { Message } from "../types";
import { ChatBubble } from "../components/Chat/ChatBubble";
import { ModelSelector } from "../components/Chat/ModelSelector";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface AdminChatProps {
  chatMessages: Message[];
  setChatMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isChatLoading: boolean;
  handleAdminChatSubmit: (queryText: string) => void;
  handleConfirmWrite: (messageId: string, token: string) => void;
  handleClarificationOption: (option: string) => void;
  onCompare: (questionText: string) => void;
  adminSessions?: { id: string; title: string; createdAt: number }[];
  activeAdminSessionId?: string | null;
  onSelectAdminSession?: (sessionId: string) => void;
  onCreateAdminSession?: () => void;
  onDeleteAdminSession?: (sessionId: string) => void;
  onRenameAdminSession?: (sessionId: string, newTitle: string) => void;
}

export const AdminChat: React.FC<AdminChatProps> = ({
  chatMessages,
  setChatMessages,
  isChatLoading,
  handleAdminChatSubmit,
  handleConfirmWrite,
  handleClarificationOption,
  onCompare,
  adminSessions = [],
  activeAdminSessionId,
  onSelectAdminSession,
  onCreateAdminSession,
  onDeleteAdminSession,
  onRenameAdminSession,
}) => {
  const [chatInput, setChatInput] = React.useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [micLang, setMicLang] = React.useState<"id-ID" | "en-US">("id-ID");

  const {
    isSupported: micSupported,
    isListening,
    interimTranscript,
    error: micError,
    start: startListening,
    stop: stopListening,
  } = useSpeechRecognition({
    lang: micLang,
    onResult: (transcript) => {
      setChatInput((prev) => (prev ? `${prev.trim()} ${transcript}` : transcript));
    },
  });

  const handleMicClick = () => {
    if (!micSupported) return;
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // Auto-scroll messages list
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  return (
    <div className="bg-surface border border-border shadow-lg rounded-3xl flex flex-col h-[650px] text-text overflow-hidden animate-fade-in font-sans">
      {/* Chat Header */}
      <div className="flex flex-wrap items-center justify-between p-4 md:p-5 border-b border-border bg-surface-2/45 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full flex items-center justify-center shadow-md">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text font-sans">
              Admin Chat Analyst
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5 font-bold font-sans">
              Administrative Mode • Write Permissions Enabled
            </p>
          </div>
        </div>

        {/* Admin Session Controls & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* New Admin Chat Button */}
          {onCreateAdminSession && (
            <button
              type="button"
              onClick={onCreateAdminSession}
              className="px-3 py-1.5 bg-accent/15 hover:bg-accent text-accent hover:text-white border border-accent/30 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer font-sans active:scale-95 shadow-sm"
              title="Create new admin chat session"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Chat</span>
            </button>
          )}

          {/* Admin Session Selector Dropdown */}
          {adminSessions.length > 0 && onSelectAdminSession && (
            <div className="flex items-center gap-1">
              <select
                value={activeAdminSessionId || ""}
                onChange={(e) => onSelectAdminSession(e.target.value)}
                className="bg-surface-hover text-xs font-bold px-3 py-1.5 border border-border rounded-xl text-text focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer font-sans max-w-[180px] truncate"
              >
                {adminSessions.map((sess) => (
                  <option key={sess.id} value={sess.id}>
                    {sess.title}
                  </option>
                ))}
              </select>

              {/* Rename Active Session Button */}
              {activeAdminSessionId && onRenameAdminSession && (
                <button
                  type="button"
                  onClick={() => {
                    const activeSess = adminSessions.find((s) => s.id === activeAdminSessionId);
                    const currentTitle = activeSess?.title || "";
                    const newTitle = prompt("Enter new title for this admin chat session:", currentTitle);
                    if (newTitle && newTitle.trim() && newTitle.trim() !== currentTitle) {
                      onRenameAdminSession(activeAdminSessionId, newTitle.trim());
                    }
                  }}
                  className="p-1.5 border border-border bg-surface-2/50 hover:bg-surface-2 text-text-muted hover:text-text rounded-xl text-xs font-bold transition-all flex items-center justify-center cursor-pointer font-sans"
                  title="Rename current session"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          <ModelSelector />

          {/* Delete Active Session */}
          {activeAdminSessionId && onDeleteAdminSession && adminSessions.length > 1 && (
            <button
              type="button"
              onClick={() => {
                if (confirm("Delete this admin chat session?")) {
                  onDeleteAdminSession(activeAdminSessionId);
                }
              }}
              className="p-1.5 border border-border bg-surface-2/50 hover:bg-red-500/20 text-text-muted hover:text-red-400 rounded-xl text-xs font-bold transition-all flex items-center justify-center cursor-pointer font-sans"
              title="Delete current session"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Chat Messages scroll area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 pr-2 scrollbar-thin">
        {chatMessages.map((msg, idx) => {
          const precedingQuestion =
            msg.sender === "ai" && idx > 0 && chatMessages[idx - 1].sender === "user"
              ? chatMessages[idx - 1].text
              : undefined;

          return (
            <ChatBubble
              key={msg.id}
              message={msg}
              questionText={precedingQuestion}
              onClarificationSelect={handleClarificationOption}
              onSuggestedSelect={handleClarificationOption}
              onConfirmWrite={handleConfirmWrite}
              onCompare={onCompare}
              hideSaveObservation={true}
            />
          );
        })}

        {/* Typing skeleton loader */}
        {isChatLoading && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl rounded-tl-none px-4 py-3 bg-surface-2 border border-border text-text-muted text-xs flex items-center gap-2 shadow-md font-sans">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent" />
              <span className="font-bold text-[10px] uppercase tracking-wider text-accent font-mono">
                AI is compiling SQL...
              </span>
              <div className="flex gap-1 items-center justify-center ml-1">
                <span
                  className="w-1.5 h-1.5 bg-text-faint rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                ></span>
                <span
                  className="w-1.5 h-1.5 bg-text-faint rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                ></span>
                <span
                  className="w-1.5 h-1.5 bg-text-faint rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                ></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions list */}
      <div className="p-4 border-t border-border bg-surface-2/35 space-y-1.5 font-sans">
        <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest block font-mono">
          Suggested Operations
        </span>
        <div className="flex flex-wrap gap-1.5">
          {[
            {
              label: "Read: Show catalog",
              cmd: "Show all products in store",
            },
            {
              label: "Read: Breakdown categories",
              cmd: "Breakdown products by category",
            },
            {
              label: "Write: Add product",
              cmd: "Insert product Lapis Cupcake category Food price 15000 cost 10000",
            },
            {
              label: "Write: Update price",
              cmd: "Update price of laptop to 12000000",
            },
            {
              label: "Write: Delete cancelled orders",
              cmd: "Delete cancelled orders",
            },
          ].map((sug, idx) => (
            <button
              type="button"
              key={idx}
              onClick={() => setChatInput(sug.cmd)}
              className="bg-surface-2 hover:bg-surface-hover border border-border text-text-muted hover:text-text px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer shadow-sm"
            >
              <span className="text-accent font-extrabold mr-1">
                {sug.label.split(":")[0]}:
              </span>
              {sug.label.split(":")[1]}
            </button>
          ))}
        </div>
      </div>

      {/* Mic error / listening feedback */}
      {(micError || isListening) && (
        <div className="px-4 pt-3 bg-surface font-sans">
          {micError && (
            <div className="text-[10px] font-bold text-danger bg-danger/10 border border-danger/25 rounded-full px-3 py-1.5 inline-flex items-center gap-1.5">
              <MicOff className="w-3 h-3" />
              {micError === "denied" ? "Microphone access blocked." : "Voice input isn't available right now."}
            </div>
          )}
          {isListening && (
            <div className="text-[10px] font-bold text-accent bg-accent-soft border border-accent/25 rounded-full px-3 py-1.5 inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              Listening{interimTranscript ? `: "${interimTranscript}"` : "..."}
            </div>
          )}
        </div>
      )}

      {/* Text Input area */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!chatInput.trim()) return;
          const text = chatInput.trim();
          setChatInput("");
          handleAdminChatSubmit(text);
        }}
        className="p-4 border-t border-border bg-surface flex gap-2 font-sans"
      >
        <input
          type="text"
          placeholder="Type an administrative operation or query (e.g. Delete cancelled orders)..."
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          className="flex-1 bg-surface-2 border border-border text-text placeholder:text-text-faint px-5 py-3 rounded-full text-sm focus:ring-2 focus:ring-accent/40 focus:border-accent focus:outline-none font-bold"
          required
        />
        <button
          type="button"
          onClick={() => setMicLang(micLang === "id-ID" ? "en-US" : "id-ID")}
          className="text-[10px] font-extrabold px-2.5 py-1 rounded-full bg-surface-2 border border-border text-text-muted hover:text-accent hover:border-accent/40 cursor-pointer transition-all shadow-2xs font-mono self-center"
          title={`Voice Language: ${micLang === "id-ID" ? "Bahasa Indonesia (id-ID)" : "English (en-US)"}. Click to switch.`}
        >
          {micLang === "id-ID" ? "🇮🇩 ID" : "🇺🇸 EN"}
        </button>
        <button
          type="button"
          onClick={handleMicClick}
          disabled={!micSupported}
          title={micSupported ? `Voice input (${micLang})` : "Voice input unavailable in this browser"}
          className={`p-3 rounded-full transition-all cursor-pointer flex items-center justify-center flex-shrink-0 disabled:cursor-not-allowed disabled:opacity-40 ${
            isListening
              ? "bg-accent text-white animate-pulse"
              : "bg-surface-2 hover:bg-surface-hover text-text-muted hover:text-accent"
          }`}
        >
          {isListening ? <Square className="w-4 h-4 fill-current" /> : <Mic className="w-4 h-4" />}
        </button>
        <button
          type="submit"
          disabled={isChatLoading}
          className="bg-accent hover:bg-accent-hover text-white font-bold px-6 py-3 rounded-full text-sm transition-all shadow-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer active:scale-95"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>
    </div>
  );
};
