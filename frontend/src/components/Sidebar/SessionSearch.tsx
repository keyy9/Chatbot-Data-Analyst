import React from "react";
import { Search } from "lucide-react";
import { useSessionStore } from "../../store/sessionStore";

export const SessionSearch: React.FC = () => {
  const { searchQuery, setSearchQuery } = useSessionStore();

  return (
    <div className="relative w-full">
      <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-text-muted" />
      <input
        type="text"
        placeholder="Search chat history..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full pl-8 pr-3 py-2 bg-white dark:bg-surface-hover/60 border border-slate-200 dark:border-border rounded-xl text-sm text-slate-800 dark:text-slate-100 placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:outline-none transition-all"
      />
    </div>
  );
};
