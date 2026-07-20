import React, { useState, useEffect } from "react";
import { useUiStore } from "../store/uiStore";
import { useProfileStore } from "../store/profileStore";
import { useAuthStore } from "../store/authStore";
import { authApi, ApiError, type AccountProfile } from "../lib/apiClient";
import { UserSidebar } from "../components/Sidebar/UserSidebar";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { MyQueryHistoryPanel } from "../components/MyQueryHistoryPanel";
import { Sparkles, Save, Calendar, Shield, Activity, User, Key, ShieldAlert } from "lucide-react";

export const Profile: React.FC = () => {
  const { theme, initializeUi } = useUiStore();
  const { profile, updateDisplayName, initializeProfile, addActivity } = useProfileStore();
  const { user: authUser } = useAuthStore();

  const [editName, setEditName] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [account, setAccount] = useState<AccountProfile | null>(null);
  const [profileError, setProfileError] = useState("");

  const [passwordLoading, setPasswordLoading] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetSuccessMsg, setResetSuccessMsg] = useState("");
  const [resetErrorMsg, setResetErrorMsg] = useState("");

  useEffect(() => {
    initializeUi();
    initializeProfile();
  }, [initializeUi, initializeProfile]);

  useEffect(() => {
    if (!authUser?.userId) return;
    authApi.getProfile(authUser.userId)
      .then((data) => {
        setAccount(data);
        setEditName(data.username || authUser.email.split("@")[0]);
      })
      .catch((error) => setProfileError(error instanceof ApiError ? error.message : "Failed to load account profile."));
  }, [authUser?.email, authUser?.userId]);

  const accountEmail = account?.email || authUser?.email || profile.email;
  const displayName = account?.username || authUser?.username || accountEmail.split("@")[0];
  const accountRole = account?.role || authUser?.role || "user";
  const joinedAt = account?.created_at ? new Date(account.created_at).toLocaleDateString() : "-";

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editName.trim() && authUser?.userId) {
      try {
        const updated = await authApi.updateProfile(authUser.userId, editName.trim());
        setAccount(updated);
        updateDisplayName(updated.username || editName.trim());
      addActivity(`Updated display name to '${editName.trim()}'`);
      setSuccessMsg("Profile updated successfully!");
      setTimeout(() => setSuccessMsg(""), 3000);
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
      addActivity("Changed account password");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to change password.";
      setResetErrorMsg(msg);
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div
      className={`h-screen flex transition-colors duration-200 overflow-hidden select-none ${
        theme === "dark" ? "bg-bg text-slate-100" : "bg-[#F8FAFC] text-slate-800"
      }`}
    >
      {/* Sidebar navigation */}
      <UserSidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto">
        {/* Header */}
        <header
          className={`h-16 flex items-center justify-between px-6 z-10 shadow-sm border-b transition-colors duration-200 flex-shrink-0 ${
            theme === "dark"
              ? "bg-bg-elevated border-border"
              : "bg-white border-slate-200"
          }`}
        >
          <div className="flex items-center gap-3">
            <span
              className={`text-sm font-semibold tracking-wide ${
                theme === "dark" ? "text-text" : "text-text"
              }`}
            >
              Analyst Profile
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-accent/10 to-teal/10 border border-accent/20 rounded-full text-[9px] font-extrabold uppercase tracking-wider text-accent">
            {accountRole}
          </div>
        </header>

        {/* Profile Card View */}
        <div className="p-8 max-w-4xl mx-auto w-full space-y-6 font-sans">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Left Card: Avatar and Details */}
            <div
              className={`p-6 rounded-2xl border shadow-md flex flex-col items-center justify-center text-center space-y-4 ${
                theme === "dark"
                  ? "bg-surface border-border"
                  : "bg-white border-slate-200"
              }`}
            >
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-accent to-teal text-white font-extrabold flex items-center justify-center shadow-lg text-2xl font-mono">
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <div className="absolute bottom-0 right-0 p-1.5 bg-accent rounded-full text-white shadow">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white leading-normal">
                  {displayName}
                </h3>
                <p className="text-[10px] text-text-faint dark:text-text-muted font-mono mt-0.5">
                  {accountEmail}
                </p>
              </div>

              <div className="flex flex-col gap-2 w-full pt-2">
                {/* Role badge */}
                <div className="flex items-center justify-between text-xs px-3 py-2 bg-slate-50 dark:bg-surface-2/45 border border-slate-100 dark:border-border rounded-xl text-slate-600 dark:text-text-muted">
                  <span className="flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-accent" />
                    Role
                  </span>
                  <span className="font-extrabold text-[10px] uppercase font-mono text-teal">
                    {accountRole}
                  </span>
                </div>

                {/* Date joined */}
                <div className="flex items-center justify-between text-xs px-3 py-2 bg-slate-50 dark:bg-surface-2/45 border border-slate-100 dark:border-border rounded-xl text-slate-600 dark:text-text-muted">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-teal" />
                    Joined Date
                  </span>
                  <span className="font-mono text-[10px]">
                    {joinedAt}
                  </span>
                </div>
              </div>
            </div>

            {/* Right Card: Edit display name & Reset Password */}
            <div
              className={`p-6 rounded-2xl border shadow-md md:col-span-2 flex flex-col justify-between ${
                theme === "dark"
                  ? "bg-surface border-border"
                  : "bg-white border-slate-200"
              }`}
            >
              <div className="text-left space-y-6 w-full">
                {/* Section 1: Display Name */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
                    <User className="w-4 h-4 text-accent" />
                    Account Settings
                  </h3>
                  <p className="text-[10px] text-text-faint dark:text-text-muted">
                    Modify display settings of the simulation analytical client.
                  </p>

                  {successMsg && (
                    <div className="p-3 bg-success/10 border border-success/25 rounded-xl text-success text-[11px] font-bold text-left animate-fade-in">
                      {successMsg}
                    </div>
                  )}
                  {profileError && <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-[11px] font-bold">{profileError}</div>}

                  <form onSubmit={handleSaveName} className="space-y-4">
                    <Input
                      label="Display Username"
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      placeholder="Analyst Name"
                      required
                    />

                    <div className="flex justify-end pt-2">
                      <Button type="submit" className="flex items-center gap-1.5 text-xs font-bold">
                        <Save className="w-4 h-4" />
                        Save Changes
                      </Button>
                    </div>
                  </form>
                </div>

                {/* Divider */}
                <div className="border-t border-border/50 dark:border-border/30 my-4" />

                {/* Section 2: Reset Password */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
                    <Key className="w-4 h-4 text-teal" />
                    Security Settings
                  </h3>
                  <p className="text-[10px] text-text-faint dark:text-text-muted">Change the password for {accountEmail}. This is saved directly to your account in the database.</p>

                  {resetSuccessMsg && (
                    <div className="p-3 bg-success/10 border border-success/25 rounded-xl text-success text-[11px] font-bold text-left animate-fade-in">
                      {resetSuccessMsg}
                    </div>
                  )}

                  {resetErrorMsg && (
                    <div className="p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-[11px] font-bold text-left animate-fade-in">
                      {resetErrorMsg}
                    </div>
                  )}

                  <form onSubmit={handleChangePassword} className="space-y-3 max-w-md">
                    <Input label="Current Password" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
                    <Input label="New Password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Minimum 8 characters" required />
                    <Input label="Confirm New Password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
                    <Button
                      type="submit"
                      isLoading={passwordLoading}
                      className="flex items-center gap-1.5 text-xs font-bold bg-surface-2 hover:bg-surface-hover text-text border border-border"
                    >
                      <ShieldAlert className="w-4 h-4 text-warning" />
                      Change Password
                    </Button>
                  </form>
                </div>
              </div>
            </div>
          </div>

          {/* Activity Log list block */}
          <div
            className={`p-6 rounded-2xl border shadow-md text-left space-y-4 ${
              theme === "dark"
                ? "bg-surface border-border"
                : "bg-white border-slate-200"
            }`}
          >
            <h3 className="text-sm font-bold text-text dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal" />
              Recent Activity Logs
            </h3>
            <div className="divide-y divide-slate-100 dark:divide-border/40">
              {profile.recentActivities.map((act, idx) => (
                <div key={idx} className="py-3 flex items-center justify-between text-xs text-slate-600 dark:text-text-muted">
                  <span className="font-semibold">{act}</span>
                  <span className="text-[8.5px] font-mono text-text-muted dark:text-text-faint">
                    Just now
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Real, self-scoped query history - the user's own rows only */}
          <MyQueryHistoryPanel />
        </div>
      </div>
    </div>
  );
};
export default Profile;
