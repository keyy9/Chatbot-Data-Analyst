import React, { useState, useEffect } from "react";
import { useUiStore } from "../store/uiStore";
import { useAuthStore } from "../store/authStore";
import { useSessionStore } from "../store/sessionStore";
import { useNoteStore } from "../store/noteStore";
import { authApi, userApi, ApiError, type AccountProfile } from "../lib/apiClient";
import type { QueryLog } from "../types/query";
import { UserSidebar } from "../components/Sidebar/UserSidebar";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";

import {
  Sparkles,
  Save,
  Calendar,
  Shield,
  Activity,
  User,
  Key,
  ShieldAlert,
  MessageSquare,
  Bookmark,
  Check,
  Search,
  Lock,
  Clock,
  BadgeCheck
} from "lucide-react";

export const Profile: React.FC = () => {
  const { theme, initializeUi } = useUiStore();
  const { user: authUser } = useAuthStore();
  const { sessions } = useSessionStore();
  const { notes } = useNoteStore();

  const [activeTab, setActiveTab] = useState<"account" | "security" | "activity">("account");
  const [editName, setEditName] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [account, setAccount] = useState<AccountProfile | null>(null);
  const [profileError, setProfileError] = useState("");
  const [activity, setActivity] = useState<QueryLog[] | null>(null);
  const [activitySearch, setActivitySearch] = useState("");

  const [passwordLoading, setPasswordLoading] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetSuccessMsg, setResetSuccessMsg] = useState("");
  const [resetErrorMsg, setResetErrorMsg] = useState("");

  useEffect(() => {
    initializeUi();
  }, [initializeUi]);

  useEffect(() => {
    if (!authUser?.userId) return;
    let cancelled = false;
    userApi
      .getMyQueryLogs(authUser.userId)
      .then((res) => { if (!cancelled) setActivity(res.logs); })
      .catch(() => { if (!cancelled) setActivity([]); });
    return () => { cancelled = true; };
  }, [authUser?.userId]);

  useEffect(() => {
    if (!authUser?.userId) return;
    authApi.getProfile(authUser.userId)
      .then((data) => {
        setAccount(data);
        setEditName(data.username || authUser.email.split("@")[0]);
      })
      .catch((error) => setProfileError(error instanceof ApiError ? error.message : "Failed to load account profile."));
  }, [authUser?.email, authUser?.userId]);

  const accountEmail = account?.email || authUser?.email || "";
  const displayName = account?.username || authUser?.username || accountEmail.split("@")[0];
  const accountRole = account?.role || authUser?.role || "user";
  const joinedAt = account?.created_at ? new Date(account.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "-";

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editName.trim() && authUser?.userId) {
      try {
        const updated = await authApi.updateProfile(authUser.userId, editName.trim());
        setAccount(updated);
        setSuccessMsg("Profile updated successfully!");
        setTimeout(() => setSuccessMsg(""), 3500);
      } catch (error) {
        setProfileError(error instanceof ApiError ? error.message : "Failed to update profile.");
      }
    }
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setResetSuccessMsg("");
    setResetErrorMsg("");
    const email = accountEmail;
    if (!email) {
      setResetErrorMsg("No email address found for your account.");
      return;
    }
    if (newPassword.length < 8) {
      setResetErrorMsg("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setResetErrorMsg("New passwords do not match.");
      return;
    }

    try {
      setPasswordLoading(true);
      await authApi.changePassword(email, currentPassword, newPassword);
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      setResetSuccessMsg("Password changed successfully.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to change password.";
      setResetErrorMsg(msg);
    } finally {
      setPasswordLoading(false);
    }
  };

  const filteredLogs = (activity || []).filter((log) =>
    log.question.toLowerCase().includes(activitySearch.toLowerCase())
  );

  return (
    <div
      className={`h-screen flex transition-colors duration-200 overflow-hidden select-none ${
        theme === "dark" ? "bg-bg text-slate-100" : "bg-[#F8FAFC] text-slate-800"
      }`}
    >
      {/* Sidebar navigation */}
      <UserSidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto font-sans">
        {/* Header */}
        <header
          className={`h-16 flex items-center justify-between px-8 z-10 shadow-xs border-b transition-colors duration-200 flex-shrink-0 ${
            theme === "dark" ? "bg-bg-elevated border-border" : "bg-white border-slate-200"
          }`}
        >
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-bold tracking-wide flex items-center gap-2 text-text">
              <User className="w-4 h-4 text-accent" />
              Analyst Profile Workspace
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-accent/10 border border-accent/25 rounded-full text-[10px] font-extrabold uppercase tracking-wider text-accent flex items-center gap-1.5 font-mono">
              <BadgeCheck className="w-3.5 h-3.5 text-accent" />
              {accountRole} privilege
            </span>
          </div>
        </header>

        {/* Content Container */}
        <div className="p-8 max-w-5xl mx-auto w-full space-y-6">
          {/* Executive Hero Banner */}
          <div className="relative rounded-3xl p-6 border border-accent/25 bg-gradient-to-r from-accent/15 via-teal/10 to-emerald-500/10 dark:from-surface dark:via-surface-2/80 dark:to-surface shadow-md overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-5 z-10 text-left">
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-accent to-teal text-white font-extrabold flex items-center justify-center shadow-lg text-2xl font-mono border-2 border-white/20">
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <div className="absolute -bottom-1 -right-1 p-1.5 bg-accent rounded-full text-white shadow-md">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-extrabold text-text dark:text-white tracking-tight">
                    {displayName}
                  </h2>
                  <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                    Active
                  </span>
                </div>
                <p className="text-xs text-text-muted font-mono mt-0.5">
                  {accountEmail}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-text-faint dark:text-text-muted mt-2 font-mono">
                  <Calendar className="w-3 h-3 text-accent" />
                  <span>Member Since: {joinedAt}</span>
                </div>
              </div>
            </div>

            {/* Quick KPI Stat Pills */}
            <div className="grid grid-cols-3 gap-3 w-full md:w-auto z-10">
              <div className="p-3 rounded-2xl bg-surface/80 dark:bg-surface-2/90 border border-border/80 text-center shadow-xs">
                <div className="flex items-center justify-center gap-1 text-accent mb-0.5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span className="text-base font-extrabold font-mono">{sessions.length}</span>
                </div>
                <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider block">Sessions</span>
              </div>

              <div className="p-3 rounded-2xl bg-surface/80 dark:bg-surface-2/90 border border-border/80 text-center shadow-xs">
                <div className="flex items-center justify-center gap-1 text-teal mb-0.5">
                  <Activity className="w-3.5 h-3.5" />
                  <span className="text-base font-extrabold font-mono">{activity?.length || 0}</span>
                </div>
                <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider block">Queries</span>
              </div>

              <div className="p-3 rounded-2xl bg-surface/80 dark:bg-surface-2/90 border border-border/80 text-center shadow-xs">
                <div className="flex items-center justify-center gap-1 text-amber-500 mb-0.5">
                  <Bookmark className="w-3.5 h-3.5 fill-current" />
                  <span className="text-base font-extrabold font-mono">{notes.length}</span>
                </div>
                <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider block">Observations</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs Bar */}
          <div className="flex items-center gap-2 border-b border-border/60 pb-3">
            <button
              onClick={() => setActiveTab("account")}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                activeTab === "account"
                  ? "bg-accent text-white shadow-xs"
                  : "bg-surface hover:bg-surface-hover text-text-muted hover:text-text border border-border"
              }`}
            >
              <User className="w-3.5 h-3.5" />
              Account Settings
            </button>

            <button
              onClick={() => setActiveTab("security")}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                activeTab === "security"
                  ? "bg-accent text-white shadow-xs"
                  : "bg-surface hover:bg-surface-hover text-text-muted hover:text-text border border-border"
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              Security &amp; Password
            </button>

            <button
              onClick={() => setActiveTab("activity")}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                activeTab === "activity"
                  ? "bg-accent text-white shadow-xs"
                  : "bg-surface hover:bg-surface-hover text-text-muted hover:text-text border border-border"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Query Activity Logs ({activity?.length || 0})
            </button>
          </div>

          {/* TAB 1: Account Settings */}
          {activeTab === "account" && (
            <div className="bg-surface border border-border rounded-3xl p-6 shadow-sm text-left space-y-6 animate-fade-in">
              <div>
                <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
                  <User className="w-4 h-4 text-accent" />
                  Account Identity &amp; Profile
                </h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Update your display username and view your database role privileges.
                </p>
              </div>

              {successMsg && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-bold flex items-center gap-2 animate-fade-in">
                  <Check className="w-4 h-4" />
                  {successMsg}
                </div>
              )}
              {profileError && (
                <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-xs font-bold">
                  {profileError}
                </div>
              )}

              <form onSubmit={handleSaveName} className="space-y-4 max-w-lg">
                <Input
                  label="Display Username"
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Analyst Name"
                  required
                />

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="p-3 rounded-xl bg-surface-2 border border-border text-xs space-y-1">
                    <span className="text-[10px] font-extrabold uppercase text-text-muted font-mono block">Role Privilege</span>
                    <span className="font-bold text-accent font-mono uppercase">{accountRole}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-2 border border-border text-xs space-y-1">
                    <span className="text-[10px] font-extrabold uppercase text-text-muted font-mono block">Joined Date</span>
                    <span className="font-bold text-text font-mono">{joinedAt}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <Button type="submit" className="flex items-center gap-2 text-xs font-bold px-6 py-2.5">
                    <Save className="w-4 h-4" />
                    Save Account Changes
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: Security & Password */}
          {activeTab === "security" && (
            <div className="bg-surface border border-border rounded-3xl p-6 shadow-sm text-left space-y-6 animate-fade-in">
              <div>
                <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
                  <Key className="w-4 h-4 text-teal" />
                  Security &amp; Authentication
                </h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Change the password for <strong className="text-text font-mono">{accountEmail}</strong>. Saved directly to database.
                </p>
              </div>

              {resetSuccessMsg && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-bold flex items-center gap-2 animate-fade-in">
                  <Check className="w-4 h-4" />
                  {resetSuccessMsg}
                </div>
              )}

              {resetErrorMsg && (
                <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-xs font-bold animate-fade-in">
                  {resetErrorMsg}
                </div>
              )}

              <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
                <Input
                  label="Current Password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  required
                />
                <Input
                  label="New Password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  required
                />
                <Input
                  label="Confirm New Password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-type new password"
                  required
                />

                <div className="pt-2">
                  <Button
                    type="submit"
                    isLoading={passwordLoading}
                    className="flex items-center gap-2 text-xs font-bold bg-accent hover:bg-accent-hover text-white px-6 py-2.5 shadow-sm"
                  >
                    <ShieldAlert className="w-4 h-4" />
                    Update Password
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: Recent Activity Logs */}
          {activeTab === "activity" && (
            <div className="bg-surface border border-border rounded-3xl p-6 shadow-sm text-left space-y-4 animate-fade-in">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-teal" />
                    Query History &amp; Audit Trail
                  </h3>
                  <p className="text-[11px] text-text-muted mt-0.5">
                    Real natural language queries asked by this account in chat.
                  </p>
                </div>

                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Search query history..."
                    value={activitySearch}
                    onChange={(e) => setActivitySearch(e.target.value)}
                    className="w-full bg-surface-2 border border-border text-text placeholder:text-text-muted pl-8 pr-3 py-1.5 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-accent/40 font-medium"
                  />
                </div>
              </div>

              <div className="divide-y divide-border/40 max-h-[450px] overflow-y-auto pr-1">
                {activity === null && (
                  <p className="py-6 text-center text-xs text-text-muted font-semibold">Loading activity logs...</p>
                )}
                {activity !== null && filteredLogs.length === 0 && (
                  <div className="py-12 text-center text-text-muted space-y-1">
                    <Activity className="w-8 h-8 mx-auto opacity-40 text-accent" />
                    <p className="text-xs font-bold">No queries found</p>
                    <p className="text-[10px]">Questions you ask in chat will be logged here.</p>
                  </div>
                )}
                {filteredLogs.map((log) => (
                  <div key={log.id} className="py-3 flex items-center justify-between gap-4 text-xs hover:bg-surface-hover/40 px-2 rounded-xl transition-colors">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                      <span className="font-semibold text-text truncate">{log.question}</span>
                    </div>
                    <span className="text-[10px] font-mono text-text-muted flex-shrink-0">
                      {new Date(log.timestamp).toLocaleString([], {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Profile;
