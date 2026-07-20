import React from "react";
import { Cpu } from "lucide-react";
import type { ModelProvider } from "../../types";
import { useUiStore } from "../../store/uiStore";

// Fixed categorical identity per provider - reused everywhere a provider is
// shown (this selector, ChatBubble badges, the comparison panel), never
// reassigned or cycled.
export const GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai";

export const PROVIDER_LABELS: Record<ModelProvider, string> = {
  groq: "Groq",
  gemini: "Gemini"
};

export const PROVIDER_COLORS: Record<ModelProvider, { text: string; bg: string; border: string; dot: string }> = {
  groq: {
    text: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/40",
    dot: "bg-accent"
  },
  gemini: {
    text: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/40",
    dot: "bg-accent"
  }
};

const PROVIDERS: ModelProvider[] = ["groq", "gemini"];

export const ModelSelector: React.FC = () => {
  const { modelProvider, setModelProvider } = useUiStore();

  return (
    <div className="flex items-center gap-1.5 text-[9px] font-sans">
      <Cpu className="w-3 h-3 text-text-muted dark:text-text-faint" />
      <div className="flex items-center gap-1 p-0.5 rounded-lg border border-slate-200 dark:border-border bg-slate-50 dark:bg-surface-hover">
        {PROVIDERS.map((provider) => {
          const isActive = modelProvider === provider;
          const colors = PROVIDER_COLORS[provider];
          return (
            <button
              key={provider}
              type="button"
              onClick={() => setModelProvider(provider)}
              className={`flex items-center gap-1 px-2 py-1 rounded-md font-bold uppercase tracking-wide transition-colors cursor-pointer ${
                isActive
                  ? `${colors.bg} ${colors.text} border ${colors.border}`
                  : "text-text-muted dark:text-text-faint border border-transparent hover:text-slate-600 dark:hover:text-text-muted"
              }`}
              title={`Answer using ${PROVIDER_LABELS[provider]}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isActive ? colors.dot : "bg-slate-300 dark:bg-slate-600"}`} />
              {PROVIDER_LABELS[provider]}
            </button>
          );
        })}
      </div>
    </div>
  );
};
