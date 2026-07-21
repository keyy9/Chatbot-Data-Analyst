import React, { useRef, useEffect } from "react";
import { Sparkles, Trash2, RefreshCw, Mic, Square, MicOff, Send } from "lucide-react";
import type { Message } from "../types";
import { ChatBubble } from "../components/Chat/ChatBubble";
import { ModelSelector } from "../components/Chat/ModelSelector";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface AdminChatProps {
  chatMessages: Message[];
  setChatMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isChatLoading: boolean;
  chatInput: string;
  setChatInput: (input: string) => void;
  handleAdminChatSubmit: (e: React.FormEvent) => void;
  handleConfirmWrite: (messageId: string, token: string) => void;
  handleClarificationOption: (option: string) => void;
  onCompare: (questionText: string) => void;
}

export const AdminChat: React.FC<AdminChatProps> = ({
  chatMessages,
  setChatMessages,
  isChatLoading,
  chatInput,
  setChatInput,
  handleAdminChatSubmit,
  handleConfirmWrite,
  handleClarificationOption,
  onCompare,
}) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const {
    isSupported: micSupported,
    isListening,
    interimTranscript,
    error: micError,
    start: startListening,
    stop: stopListening,
  } = useSpeechRecognition({
    onResult: (transcript) => {
      setChatInput(chatInput ? `${chatInput.trim()} ${transcript}` : transcript);
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
      <div className="flex items-center justify-between p-5 border-b border-border bg-surface-2/45">
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
        <div className="flex items-center gap-3">
          <ModelSelector />
          <button
            type="button"
            onClick={() =>
              setChatMessages([
                {
                  id: "welcome",
                  sender: "ai",
                  text: "Hello! I am your AI Data Analyst assistant with administrative database privileges. Ask me anything about our database, or perform data operations (INSERT, UPDATE, DELETE). For example, try asking 'Show all products in the store' or 'Delete all orders with cancelled status'.",
                  timestamp: Date.now(),
                },
              ])
            }
            className="px-3 py-1.5 border border-border bg-surface-2/50 hover:bg-surface-2 rounded-full text-text-muted hover:text-text text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer font-sans"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear History
          </button>
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
              onConfirmWrite={handleConfirmWrite}
              onCompare={onCompare}
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
        onSubmit={handleAdminChatSubmit}
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
          onClick={handleMicClick}
          disabled={!micSupported}
          title={micSupported ? "Voice input" : "Voice input unavailable in this browser"}
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
