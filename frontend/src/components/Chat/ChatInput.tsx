import React, { useState, useRef, useEffect } from "react";
import { Mic, Square, MicOff, Send, AlertCircle, Sparkles } from "lucide-react";
import { useChatStore } from "../../store/chatStore";
import { useSessionStore } from "../../store/sessionStore";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";
import { VoiceWaveform } from "./VoiceWaveform";
import { QuickAnalyticsLibrary } from "./QuickAnalyticsLibrary";

export const ChatInput: React.FC = () => {
  const { submitUserQuery, isLoading } = useChatStore();
  const { activeSessionId } = useSessionStore();
  const [text, setText] = useState("");
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [micLang, setMicLang] = useState<"id-ID" | "en-US">("id-ID");
  const inputRef = useRef<HTMLInputElement | null>(null);

  const {
    isSupported: micSupported,
    isListening,
    interimTranscript,
    error: micError,
    start: startListening,
    stop: stopListening,
    resetError: resetMicError,
  } = useSpeechRecognition({
    lang: micLang,
    onResult: (transcript) => {
      setText((prev) => (prev ? `${prev.trim()} ${transcript}` : transcript));
    },
  });

  useEffect(() => {
    if (micError) {
      const timeout = setTimeout(resetMicError, 6000);
      return () => clearTimeout(timeout);
    }
  }, [micError, resetMicError]);

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading || !activeSessionId) return;

    submitUserQuery(activeSessionId, text.trim());
    setText("");
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleMicClick = () => {
    if (!micSupported) return;
    if (isListening) {
      stopListening();
    } else {
      startListening();
      inputRef.current?.focus();
    }
  };

  const handleSelectTemplate = (queryText: string) => {
    if (activeSessionId) {
      submitUserQuery(activeSessionId, queryText);
    }
  };

  return (
    <div className="w-full space-y-2 font-sans select-none">
      {/* Quick Analytics Library Modal */}
      <QuickAnalyticsLibrary
        isOpen={isLibraryOpen}
        onClose={() => setIsLibraryOpen(false)}
        onSelectQuery={handleSelectTemplate}
      />

      {/* Mic error banner */}
      {micError && (
        <div className="flex items-center gap-2 p-3 bg-danger/10 border border-danger/25 rounded-2xl text-danger text-xs text-left animate-rise-in shadow-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-bold">
              {micError === "denied"
                ? "Microphone access is blocked."
                : micError === "unsupported"
                ? "Voice input isn't supported in this browser."
                : micError === "no-speech"
                ? "Didn't catch that - no speech detected."
                : "Voice input hit a problem."}
            </span>{" "}
            Please type your question instead.
          </div>
          <button
            onClick={resetMicError}
            className="text-[10px] font-bold hover:underline cursor-pointer bg-danger/10 px-2 py-0.5 rounded"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Listening indicator with VoiceWaveform */}
      {isListening && (
        <div className="flex items-center justify-between p-3 bg-accent-soft border border-accent/25 rounded-2xl text-accent text-xs shadow-sm animate-rise-in">
          <div className="flex items-center gap-2.5 min-w-0">
            <VoiceWaveform isListening={isListening} />
            {interimTranscript && (
              <span className="text-text-muted font-medium truncate">{interimTranscript}</span>
            )}
          </div>
          <button
            onClick={stopListening}
            className="text-[9px] font-bold hover:underline cursor-pointer flex-shrink-0"
          >
            Stop
          </button>
        </div>
      )}

      {/* Main Form input bar */}
      <form onSubmit={handleSend} className="relative flex items-center gap-2">
        <button
          type="button"
          onClick={() => setIsLibraryOpen(true)}
          className="px-3.5 py-3 rounded-full bg-accent/10 border border-accent/20 hover:bg-accent hover:text-white text-accent transition-all cursor-pointer flex items-center gap-1.5 text-xs font-bold shadow-sm flex-shrink-0"
          title="Open Quick Analytics Preset Templates"
        >
          <Sparkles className="w-4 h-4" />
          <span className="hidden sm:inline">Quick Analytics</span>
        </button>

        <input
          ref={inputRef}
          type="text"
          placeholder="Ask Lapis anything about retail database..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={isLoading || !activeSessionId}
          className="flex-1 bg-surface-2 border border-border text-text placeholder:text-text-faint pl-5 pr-28 py-4.5 rounded-full text-sm focus:ring-2 focus:ring-accent/40 focus:border-accent focus:outline-none transition-all shadow-sm font-semibold py-[17px]"
        />

        <div className="absolute right-3 flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setMicLang(micLang === "id-ID" ? "en-US" : "id-ID")}
            className="text-[10px] font-extrabold px-2 py-1 rounded-full bg-surface border border-border/80 text-text-muted hover:text-accent hover:border-accent/40 cursor-pointer transition-all shadow-2xs font-mono"
            title={`Voice Language: ${micLang === "id-ID" ? "Bahasa Indonesia (id-ID)" : "English (en-US)"}. Click to switch.`}
          >
            {micLang === "id-ID" ? "🇮🇩 ID" : "🇺🇸 EN"}
          </button>

          <button
            type="button"
            onClick={handleMicClick}
            disabled={isLoading || !activeSessionId || !micSupported}
            className={`p-2.5 rounded-full transition-all cursor-pointer flex items-center justify-center disabled:cursor-not-allowed disabled:opacity-40 ${
              isListening
                ? "bg-accent text-white animate-pulse"
                : !micSupported
                ? "bg-surface text-text-faint"
                : "bg-surface hover:bg-surface-hover text-text-muted hover:text-accent"
            }`}
            title={micSupported ? `Voice input (${micLang})` : "Voice input unavailable in this browser"}
          >
            {isListening ? (
              <Square className="w-4 h-4 fill-current" />
            ) : !micSupported ? (
              <MicOff className="w-4 h-4" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>

          <button
            type="submit"
            disabled={!text.trim() || isLoading || !activeSessionId}
            className="p-2.5 bg-accent hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-full shadow-sm transition-all flex items-center justify-center cursor-pointer active:scale-95"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
