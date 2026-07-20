import { useEffect, useRef, useState } from "react";
import { useUiStore } from "../store/uiStore";
import { useSessionStore } from "../store/sessionStore";
import { useChatStore } from "../store/chatStore";
import { useNoteStore } from "../store/noteStore";
import { UserSidebar } from "../components/Sidebar/UserSidebar";
import { ChatWelcome } from "../components/Chat/ChatWelcome";
import { ChatBubble } from "../components/Chat/ChatBubble";
import { ChatInput } from "../components/Chat/ChatInput";
import { ModelSelector } from "../components/Chat/ModelSelector";
import { ComparisonModal } from "../components/Chat/ComparisonModal";
import { NotesDrawer } from "../components/Notes/NotesDrawer";
import { Loading } from "../components/UI/Loading";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { Sun, Moon } from "lucide-react";
import type { CompareResponse } from "../lib/apiClient";

export const ChatPage: React.FC = () => {
  const { theme, setTheme, initializeUi } = useUiStore();
  const { activeSessionId, initializeSessions, sessions } = useSessionStore();
  const { messagesBySession, isLoading, submitClarificationAnswer, compareQuestion, initializeChat } = useChatStore();
  const { initializeNotes } = useNoteStore();

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const [compareState, setCompareState] = useState<{
    questionText: string;
    isLoading: boolean;
    result: CompareResponse | null;
    error: string | null;
  } | null>(null);

  const handleCompare = async (questionText: string) => {
    if (!activeSessionId) return;
    setCompareState({ questionText, isLoading: true, result: null, error: null });
    try {
      const result = await compareQuestion(activeSessionId, questionText);
      setCompareState({ questionText, isLoading: false, result, error: result ? null : "Not logged in." });
    } catch {
      setCompareState({ questionText, isLoading: false, result: null, error: "Comparison failed. Please try again." });
    }
  };

  useEffect(() => {
    initializeUi();
    initializeSessions();
    initializeNotes();
    initializeChat();
  }, [initializeUi, initializeSessions, initializeNotes, initializeChat]);

  const activeMessages = activeSessionId ? (messagesBySession[activeSessionId] || []) : [];

  // Autoscroll when new messages appear or isLoading state changes
  useAutoScroll(messagesEndRef, activeMessages.length + (isLoading ? 1 : 0));

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const getActiveSessionTitle = () => {
    const s = sessions.find((item) => item.id === activeSessionId);
    return s ? s.title : "Analytical Chat";
  };

  return (
    <div className="h-screen flex overflow-hidden select-none bg-bg text-text">
      {/* Sidebar navigation */}
      <UserSidebar />

      {/* Main chat viewport */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* Header bar */}
        <header className="h-16 flex items-center justify-between px-6 z-10 shadow-sm border-b border-border bg-bg-elevated glass-panel">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold tracking-wide text-text">
              {getActiveSessionTitle()}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* LLM provider selector */}
            <ModelSelector />

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full border border-border bg-surface-2/60 hover:bg-surface-hover text-warning transition-all cursor-pointer flex items-center justify-center"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4 text-teal-strong" />}
            </button>

            {/* Read-Only Status pill */}
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-accent-soft border border-accent/20 rounded-full text-[9px] font-extrabold uppercase tracking-wider text-accent">
              <span className="w-1 h-1 bg-accent rounded-full animate-ping"></span>
              Read-Only Mode
            </div>
          </div>
        </header>

        {/* Conversation feed scroll zone */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 flex flex-col scrollbar-thin">
          {activeMessages.length === 0 ? (
            <ChatWelcome />
          ) : (
            <div className="space-y-6 max-w-3xl mx-auto w-full">
              {activeMessages.map((msg, idx) => {
                // The AI message itself carries no question field - it's
                // the preceding user turn. Only needed for export.
                const precedingQuestion =
                  msg.sender === "ai" && idx > 0 && activeMessages[idx - 1].sender === "user"
                    ? activeMessages[idx - 1].text
                    : undefined;

                return (
                  <ChatBubble
                    key={msg.id}
                    message={msg}
                    questionText={precedingQuestion}
                    onClarificationSelect={(option) =>
                      activeSessionId && submitClarificationAnswer(activeSessionId, option)
                    }
                    onCompare={handleCompare}
                  />
                );
              })}

              {/* Waiting response loading state */}
              {isLoading && <Loading />}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Floating Chat Input bar */}
        <div className="p-6 max-w-3xl mx-auto w-full border-t border-border/40 bg-transparent">
          <ChatInput />
        </div>
      </div>

      {/* Drawer panel: Saved observations notes */}
      <NotesDrawer />

      {/* Per-query model comparison modal */}
      {compareState && (
        <ComparisonModal
          questionText={compareState.questionText}
          isLoading={compareState.isLoading}
          result={compareState.result}
          error={compareState.error}
          onClose={() => setCompareState(null)}
        />
      )}
    </div>
  );
};
export default ChatPage;
