import React from "react";
import {
  LayoutDashboard,
  FileSearch,
  Users,
  ShieldCheck,
  Award,
  MessageSquare,
  ChevronLeft,
} from "lucide-react";
import logoImg from "../assets/logo.png";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  theme: "dark" | "light";
  isTesting: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  sidebarCollapsed,
  setSidebarCollapsed,
  isTesting,
}) => {
  const [width, setWidth] = React.useState(() => {
    const saved = localStorage.getItem("admin_sidebar_width");
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
      localStorage.setItem("admin_sidebar_width", String(newWidth));
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

  const getSidebarItemClass = (tab: string) => {
    const isActive = activeTab === tab;
    return `w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm font-bold transition-all duration-200 ${
      isActive
        ? "bg-accent-soft text-accent font-semibold"
        : "text-text-muted hover:bg-surface-2 hover:text-text cursor-pointer"
    }`;
  };

  return (
    <aside
      className={`flex flex-col justify-between border-r border-border bg-bg-elevated text-text z-20 relative ${
        isDragging ? "" : "transition-all duration-300"
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
      <div>
        {/* Logo Brand area - click to collapse/expand the sidebar */}
        <button
          type="button"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
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
                  Analyst Admin
                </span>
              </div>
            )}
          </div>
          {!sidebarCollapsed && <ChevronLeft className="w-4 h-4 text-text-faint flex-shrink-0" />}
        </button>

        {/* Nav links */}
        <nav className="p-3 space-y-6">
          {/* Dashboard Section */}
          <div>
            {!sidebarCollapsed && (
              <p className="px-3 text-[9px] font-bold text-text-faint uppercase tracking-widest mb-2 font-mono">
                Main
              </p>
            )}
            <button
              type="button"
              onClick={() => setActiveTab("dashboard")}
              className={getSidebarItemClass("dashboard")}
            >
              <LayoutDashboard className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-sans">Dashboard</span>}
            </button>
          </div>

          {/* Monitoring Section */}
          <div>
            {!sidebarCollapsed && (
              <p className="px-3 text-[9px] font-bold text-text-faint uppercase tracking-widest mb-2 font-mono">
                Monitoring
              </p>
            )}
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => setActiveTab("query-logs")}
                className={getSidebarItemClass("query-logs")}
              >
                <FileSearch className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span className="font-sans">Query Logs</span>}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("user-activity")}
                className={getSidebarItemClass("user-activity")}
              >
                <Users className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span className="font-sans">User Activity</span>}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("user-management")}
                className={getSidebarItemClass("user-management")}
              >
                <ShieldCheck className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span className="font-sans">User Management</span>}
              </button>
            </div>
          </div>

          {/* Evaluation Section */}
          <div>
            {!sidebarCollapsed && (
              <p className="px-3 text-[9px] font-bold text-text-faint uppercase tracking-widest mb-2 font-mono">
                Evaluation
              </p>
            )}
            <button
              type="button"
              onClick={() => setActiveTab("benchmark")}
              className={`${getSidebarItemClass("benchmark")} relative`}
            >
              <Award className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-sans">Benchmark</span>}
              {isTesting && (
                <span className="absolute right-2 top-3.5 w-2 h-2 bg-accent rounded-full animate-ping"></span>
              )}
            </button>
          </div>

          {/* Admin Section */}
          <div>
            {!sidebarCollapsed && (
              <p className="px-3 text-[9px] font-bold text-text-faint uppercase tracking-widest mb-2 font-mono">
                Admin
              </p>
            )}
            <button
              type="button"
              onClick={() => setActiveTab("admin-chat")}
              className={getSidebarItemClass("admin-chat")}
            >
              <MessageSquare className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-sans">Admin Chat</span>}
            </button>
          </div>
        </nav>
      </div>
    </aside>
  );
};
