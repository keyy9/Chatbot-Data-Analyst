import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Sparkles, MessageSquarePlus, FileText, User, LogOut, ChevronLeft, Database } from "lucide-react";
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

  const [width, setWidth] = React.useState(() => {
    const saved = localStorage.getItem("sidebar_width");
    return saved ? Number(saved) : 288;
  });
  const [isDragging, setIsDragging] = React.useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const newWidth = Math.max(200, Math.min(450, startWidth + (moveEvent.clientX - startX)));
      setWidth(newWidth);
      localStorage.setItem("sidebar_width", String(newWidth));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const currentWidth = sidebarCollapsed ? 64 : width;

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

  const handleDataClick = () => {
    navigate("/data");
  };

  const navItemClass = (active = false) =>
    `w-full flex items-center gap-3 p-2.5 rounded-2xl text-sm font-bold transition-all cursor-pointer ${
      active ? "bg-surface-2 text-text" : "text-text-muted hover:text-text hover:bg-surface-2"
    } ${sidebarCollapsed ? "justify-center" : ""}`;

  return (
    <aside
      className={`h-screen flex flex-col border-r border-border bg-bg-elevated text-text z-30 relative ${
        isDragging ? "" : "transition-[width] duration-300"
      }`}
      style={{ width: `${currentWidth}px` }}
    >
      {!sidebarCollapsed && (
        <div
          onMouseDown={handleMouseDown}
          className={`absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-accent/40 hover:w-1.5 transition-all z-50 ${
            isDragging ? "bg-accent w-1.5" : ""
          }`}
          title="Drag to resize sidebar"
        />
      )}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Brand logo header - click to collapse/expand the sidebar */}
        <button
          type="button"
          onClick={toggleSidebar}
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`w-full h-16 flex-shrink-0 flex items-center border-b border-border cursor-pointer hover:bg-surface-2 transition-colors ${
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
        <div className="px-3 pt-3 space-y-1 flex-shrink-0">
          <button
            onClick={handleChatClick}
            className={navItemClass(location.pathname === "/chat")}
            title="Chat Room"
          >
            <Sparkles className="w-4 h-4 text-sand" />
            {!sidebarCollapsed && <span>Chat Room</span>}
          </button>
          <button
            onClick={handleDataClick}
            className={navItemClass(location.pathname === "/data")}
            title="Business Database"
          >
            <Database className="w-4 h-4 text-teal" />
            {!sidebarCollapsed && <span>Raw Data</span>}
          </button>
        </div>

        {/* Action button: New Chat */}
        <div className="p-3 pt-2 flex-shrink-0">
          <button
            onClick={handleNewChat}
            className={`w-full bg-accent hover:bg-accent-hover text-white font-bold p-2.5 rounded-2xl shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer text-sm active:scale-[0.98] ${
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
            <div className="flex-shrink-0">
              <SessionSearch />
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin">
              <SessionList />
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Footer buttons */}
      <div className="p-3 border-t border-border space-y-1.5 flex-shrink-0">
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
          className={`w-full flex items-center gap-3 p-2.5 rounded-2xl text-sm font-bold transition-all text-text-muted hover:text-danger hover:bg-danger/10 cursor-pointer ${
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
