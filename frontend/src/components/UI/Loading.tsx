import React from "react";

export const Loading: React.FC = () => {
  return (
    <div className="flex justify-start w-full animate-pulse">
      <div className="max-w-[85%] rounded-2xl rounded-tl-none px-4 py-3 bg-surface-2 border border-border text-text-muted text-xs space-y-2 shadow-md w-72">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 bg-accent/30 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
          <div className="h-3 w-3 bg-accent/30 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
          <div className="h-3 w-3 bg-accent/30 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
          <span className="text-[9px] uppercase tracking-wider text-accent/80 font-bold font-mono">
            AI is compiling SQL...
          </span>
        </div>
        <div className="space-y-1.5 pt-1">
          <div className="h-2.5 bg-slate-800 rounded w-5/6"></div>
          <div className="h-2.5 bg-slate-800 rounded w-4/6"></div>
        </div>
      </div>
    </div>
  );
};
