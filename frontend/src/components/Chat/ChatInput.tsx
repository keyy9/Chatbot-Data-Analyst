import React, { useState, useRef, useEffect } from "react";
import { Mic, Square, MicOff, Send, AlertCircle } from "lucide-react";
import { useChatStore } from "../../store/chatStore";
import { useSessionStore } from "../../store/sessionStore";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";

export const ChatInput: React.FC = () => {
  const { submitUserQuery, isLoading } = useChatStore();
  const { activeSessionId } = useSessionStore();
  const [text, setText] = useState("");
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

  return (
    <div className="w-full space-y-2 font-sans select-none">
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

      {/* Listening indicator */}
      {isListening && (
        <div className="flex items-center justify-between p-3 bg-accent-soft border border-accent/25 rounded-2xl text-accent text-xs shadow-sm animate-rise-in">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex items-end gap-0.5 h-3 flex-shrink-0">
              <span className="w-0.5 bg-accent rounded-full animate-mic-wave" style={{ animationDelay: "0ms" }} />
              <span className="w-0.5 bg-accent rounded-full animate-mic-wave" style={{ animationDelay: "150ms" }} />
              <span className="w-0.5 bg-accent rounded-full animate-mic-wave" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="font-bold tracking-wide flex-shrink-0">Listening...</span>
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
        <input
          ref={inputRef}
          type="text"
          placeholder="Ask Lapis anything about retail database..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={isLoading || !activeSessionId}
          className="flex-1 bg-surface-2 border border-border text-text placeholder:text-text-faint pl-4 pr-24 py-3.5 rounded-full text-xs focus:ring-2 focus:ring-accent/40 focus:border-accent focus:outline-none transition-all shadow-sm font-semibold"
        />

        <div className="absolute right-2 flex items-center gap-1.5">
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
            title={micSupported ? "Voice input" : "Voice input unavailable in this browser"}
          >
            {isListening ? (
              <Square className="w-3.5 h-3.5 fill-current" />
            ) : !micSupported ? (
              <MicOff className="w-3.5 h-3.5" />
            ) : (
              <Mic className="w-3.5 h-3.5" />
            )}
          </button>

          <button
            type="submit"
            disabled={!text.trim() || isLoading || !activeSessionId}
            className="p-2.5 bg-accent hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-full shadow-sm transition-all flex items-center justify-center cursor-pointer active:scale-95"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
};
