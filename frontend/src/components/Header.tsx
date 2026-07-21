import React from "react";
import { Sun, Moon, LogOut } from "lucide-react";
import { useAuthStore } from "../store/authStore";

interface HeaderProps {
  activeTab: string;
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
  apiError: boolean;
  handleLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  theme,
  setTheme,
  handleLogout,
}) => {
  const { user } = useAuthStore();
  const accountLabel = user?.role === "admin" ? "Admin" : "User";
  const accountEmail = user?.email || "Unknown account";
  const avatarInitial = accountEmail.charAt(0).toUpperCase() || "?";

  const getTabLabel = (tab: string) => {
    switch (tab) {
      case "dashboard":
        return "Dashboard";
      case "query-logs":
        return "Query Logs";
      case "user-activity":
        return "User Activity";
      case "user-management":
        return "User Management";
      case "benchmark":
        return "Benchmark";
      case "admin-chat":
        return "Admin Chat";
      case "db-editor":
        return "Database Editor";
      default:
        return tab;
    }
  };

  return (
    <header className="h-16 flex items-center justify-between px-6 z-10 bg-bg-elevated border-b border-border glass-panel">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-text-muted">
          Conversational Analyst
        </span>
        <span className="text-text-faint">/</span>
        <span className="text-sm font-semibold capitalize text-text">
          {getTabLabel(activeTab)}
        </span>
      </div>

      {/* Header Indicators / Controls */}
      <div className="flex items-center gap-6">
        {/* Theme Toggle & Profile Dropdown & Logout */}
        <div className="flex items-center gap-3">
          {/* Theme Toggle Button */}
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-full border border-border bg-surface-2/60 hover:bg-surface-hover text-text-muted hover:text-text transition-all cursor-pointer flex items-center justify-center"
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? <Sun className="w-4 h-4 text-warning" /> : <Moon className="w-4 h-4 text-teal" />}
          </button>

          <div className="text-right">
            <p className="text-sm font-semibold leading-none text-text">{accountLabel}</p>
            <p className="text-[10px] font-medium mt-1 text-text-muted">{accountEmail}</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-accent text-white flex items-center justify-center font-bold shadow-sm shadow-accent/30 text-sm font-sans">
            {avatarInitial}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="ml-2 px-2.5 py-1.5 border border-border bg-surface-2/60 hover:bg-danger/10 hover:border-danger/30 hover:text-danger rounded-full text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer text-text-muted"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};
