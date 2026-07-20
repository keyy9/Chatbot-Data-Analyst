import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Sparkles, MessageSquarePlus, FileText, User, LogOut, ChevronLeft } from "lucide-react";
import { useUiStore } from "../../store/uiStore";
import { useSessionStore } from "../../store/sessionStore";
import { useAuthStore } from "../../store/authStore";
import { SessionSearch } from "./SessionSearch";
import { SessionList } from "./SessionList";
import logoImg from "../../assets/logo.png";

export const UserSidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar, setSidebarCollapsed, toggleNotesDrawer } = useUiStore();

  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setSidebarCollapsed(true);
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [setSidebarCollapsed]);
  const { createSession } = useSessionStore();
  const { logout } = useAuthStore();

  const handleNewChat = () => {
    createSession();
    // Redirect to chat if not already on the chat page
    if (location.pathname !== "/chat") {
      navigate("/chat");
    }
  };

  const handleLogoutClick = () => {
    if (confirm("Are you sure you want to log out?")) {
      logout();
      navigate("/login");
    }
  };

  const handleProfileClick = () => {
    navigate("/profile");
  };

  const handleChatClick = () => {
    navigate("/chat");
  };

  const navItemClass = (active = false) =>
    `w-full flex items-center gap-3 p-2.5 rounded-2xl text-xs font-bold transition-all cursor-pointer ${
      active ? "bg-surface-2 text-text" : "text-text-muted hover:text-text hover:bg-surface-2"
    } ${sidebarCollapsed ? "justify-center" : ""}`;

  return (
    <aside
      className={`h-screen flex flex-col justify-between transition-all duration-300 border-r border-border bg-bg-elevated text-text z-30 ${
        sidebarCollapsed ? "w-16" : "w-72"
      }`}
    >
      <div>
        {/* Brand logo header - click to collapse/expand the sidebar */}
        <button
          type="button"
          onClick={toggleSidebar}
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`w-full h-16 flex items-center border-b border-border cursor-pointer hover:bg-surface-2 transition-colors ${
            sidebarCollapsed ? "justify-center px-2" : "justify-between px-4"
          }`}
        >
          <div className={`flex items-center gap-3 ${sidebarCollapsed ? "" : "overflow-hidden"}`}>
            <div className="w-9 h-9 bg-accent rounded-xl flex items-center justify-center shadow-sm shadow-accent/30 flex-shrink-0">
              <img src={logoImg} alt="Lapis AI Logo" className="w-5 h-5 object-contain invert brightness-0" />
            </div>
            {!sidebarCollapsed && (
              <div className="text-left leading-tight">
                <span className="font-semibold tracking-wide block text-text font-sans">
                  Lapis AI
                </span>
                <span className="text-[9px] text-accent block uppercase font-bold tracking-wider font-mono">
                  Analyst Client
                </span>
              </div>
            )}
          </div>
          {!sidebarCollapsed && <ChevronLeft className="w-4 h-4 text-text-faint flex-shrink-0" />}
        </button>

        {/* Navigation Menu */}
        <div className="px-3 pt-3 space-y-1">
          <button
            onClick={handleChatClick}
            className={navItemClass(location.pathname === "/chat")}
            title="Chat Room"
          >
            <Sparkles className="w-4 h-4 text-sand" />
            {!sidebarCollapsed && <span>Chat Room</span>}
          </button>
        </div>

        {/* Action button: New Chat */}
        <div className="p-3 pt-2">
          <button
            onClick={handleNewChat}
            className={`w-full bg-accent hover:bg-accent-hover text-white font-bold p-2.5 rounded-2xl shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer text-xs active:scale-[0.98] ${
              sidebarCollapsed ? "px-0" : ""
            }`}
          >
            <MessageSquarePlus className="w-4 h-4" />
            {!sidebarCollapsed && <span>New Chat</span>}
          </button>
        </div>

        {/* Sessions Filter/Search & List */}
        {!sidebarCollapsed && (
          <div className="px-3 py-1 space-y-3 flex-1 flex flex-col min-h-0 overflow-hidden">
            <SessionSearch />
            <div className="overflow-y-auto max-h-[calc(100vh-320px)] scrollbar-thin">
              <SessionList />
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Footer buttons */}
      <div className="p-3 border-t border-border space-y-1.5">
        {/* Notes Toggle Shortcut */}
        <button
          onClick={() => {
            toggleNotesDrawer(true);
            if (location.pathname !== "/chat") {
              navigate("/chat");
            }
          }}
          className={navItemClass()}
          title="Analytical observations"
        >
          <FileText className="w-4 h-4 text-accent" />
          {!sidebarCollapsed && <span>Saved Observations</span>}
        </button>

        {/* Profile Link */}
        <button
          onClick={handleProfileClick}
          className={navItemClass(location.pathname === "/profile")}
          title="Analyst profile"
        >
          <User className="w-4 h-4 text-teal" />
          {!sidebarCollapsed && <span>Analyst Profile</span>}
        </button>

        {/* Logout */}
        <button
          onClick={handleLogoutClick}
          className={`w-full flex items-center gap-3 p-2.5 rounded-2xl text-xs font-bold transition-all text-text-muted hover:text-danger hover:bg-danger/10 cursor-pointer ${
            sidebarCollapsed ? "justify-center" : ""
          }`}
          title="Logout account"
        >
          <LogOut className="w-4 h-4 text-danger" />
          {!sidebarCollapsed && <span>Log Out</span>}
        </button>
      </div>
    </aside>
  );
};
