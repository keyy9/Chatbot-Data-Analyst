import React from "react";
import { HelpCircle } from "lucide-react";

interface ClarificationCardProps {
  options: string[];
  onSelect: (option: string) => void;
}

export const ClarificationCard: React.FC<ClarificationCardProps> = ({ options, onSelect }) => {
  return (
    <div className="bg-amber-500/10 border border-amber-500/25 p-4 rounded-xl space-y-3 text-left w-full max-w-md animate-fade-in font-sans">
      <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-bold text-xs">
        <HelpCircle className="w-4 h-4" />
        Which query did you mean?
      </div>
      <div className="flex flex-col gap-2">
        {options.map((opt, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(opt)}
            className="w-full bg-white dark:bg-surface-hover hover:bg-slate-50 dark:hover:bg-[#1D3F3A] border border-slate-200 dark:border-border text-slate-700 dark:text-text p-2.5 rounded-lg text-xs text-left font-medium transition-all shadow-sm cursor-pointer hover:border-accent/50"
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
};
