import React, { useState } from "react";
import { User, X, Edit3, Lock, Unlock, Trash2, KeyRound } from "lucide-react";
import type { ManagedUser } from "../../types/user";

type ActionResult = { success: boolean; error?: string; message?: string };

interface UserProfileDrawerProps {
  selectedManagedUser: ManagedUser | null;
  setSelectedManagedUser: (user: ManagedUser | null) => void;
  setEditingManagedUser: (user: ManagedUser | null) => void;
  setDeletingManagedUser: (user: ManagedUser | null) => void;
  onToggleStatus: (user: ManagedUser) => Promise<void>;
  onTriggerResetPassword: (targetId: string) => Promise<ActionResult>;
  showToast: (msg: string) => void;
}

export const UserProfileDrawer: React.FC<UserProfileDrawerProps> = ({
  selectedManagedUser,
  setSelectedManagedUser,
  setEditingManagedUser,
  setDeletingManagedUser,
  onToggleStatus,
  onTriggerResetPassword,
  showToast,
}) => {
  const [isSendingReset, setIsSendingReset] = useState(false);

  if (!selectedManagedUser) return null;
  const isManageable = selectedManagedUser.role !== "Admin";

  const handleResetPassword = async () => {
    setIsSendingReset(true);
    const res = await onTriggerResetPassword(selectedManagedUser.id);
    setIsSendingReset(false);
    showToast(res.success ? `📧 ${res.message}` : `⚠️ ${res.error || "Failed to send reset email"}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        onClick={() => setSelectedManagedUser(null)}
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs transition-opacity cursor-pointer"
      ></div>

      <div className="relative w-full max-w-md bg-surface border-l border-border h-full shadow-2xl flex flex-col justify-between animate-slide-in text-text z-10 font-sans">
        <div className="px-6 py-4 border-b border-border bg-surface-2/50 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-text uppercase tracking-wider flex items-center gap-2">
              <User className="w-4 h-4 text-accent" />
              User Profile Details
            </h3>
          </div>
          <button
            type="button"
            onClick={() => setSelectedManagedUser(null)}
            className="text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center gap-4 bg-surface-2/45 border border-border p-4 rounded-xl shadow-md">
            <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-accent to-teal text-white font-extrabold flex items-center justify-center shadow-lg text-lg font-mono">
              {selectedManagedUser.username.charAt(0).toUpperCase()}
            </div>
            <div>
              <h4 className="text-sm font-bold text-text leading-normal">
                {selectedManagedUser.username}
              </h4>
              <p className="text-xs text-text-muted font-mono mt-0.5">
                {selectedManagedUser.email}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span
                  className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[9px] font-bold ${
                    selectedManagedUser.role === "Admin"
                      ? "bg-teal/10 text-teal border border-teal/20"
                      : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                  }`}
                >
                  {selectedManagedUser.role}
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold ${
                    selectedManagedUser.status === "Active"
                      ? "bg-success/10 text-success border border-success/20"
                      : selectedManagedUser.status === "Suspended"
                        ? "bg-danger/10 text-danger border border-danger/20"
                        : "bg-slate-500/10 text-text-muted border border-slate-500/20"
                  }`}
                >
                  {selectedManagedUser.status}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="bg-surface-2/25 p-3 rounded-lg border border-border/60">
              <span className="text-[9px] font-bold text-text-faint uppercase block">
                Created Date
              </span>
              <span className="text-text font-bold block mt-1 font-mono">
                {selectedManagedUser.createdAt}
              </span>
            </div>
            <div className="bg-surface-2/25 p-3 rounded-lg border border-border/60">
              <span className="text-[9px] font-bold text-text-faint uppercase block">
                Last Active
              </span>
              <span className="text-text font-bold block mt-1 font-mono">
                {selectedManagedUser.lastActive}
              </span>
            </div>
            <div className="bg-surface-2/25 p-3 rounded-lg border border-border/60">
              <span className="text-[9px] font-bold text-text-faint uppercase block">
                Total Queries
              </span>
              <span className="text-text font-bold block mt-1 font-mono">
                {selectedManagedUser.totalQueries}
              </span>
            </div>
            <div className="bg-surface-2/25 p-3 rounded-lg border border-border/60">
              <span className="text-[9px] font-bold text-text-faint uppercase block">
                Success Rate
              </span>
              <span className="text-text font-bold block mt-1 font-mono">
                {(selectedManagedUser.successRate * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {!isManageable && (
            <div className="text-[10px] text-text-muted italic bg-surface-2/45 border border-border/60 p-3 rounded-lg leading-relaxed">
              Admin accounts can't be edited, suspended, or deleted from this panel.
            </div>
          )}
        </div>

        {isManageable && (
          <div className="p-4 border-t border-border bg-surface-2/45 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setEditingManagedUser(selectedManagedUser)}
              className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text font-bold px-3 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer flex items-center justify-center gap-1"
            >
              <Edit3 className="w-3.5 h-3.5 text-blue-400" />
              Edit Username
            </button>

            <button
              type="button"
              onClick={() => onToggleStatus(selectedManagedUser)}
              className={`border font-bold px-3 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer flex items-center justify-center gap-1 ${
                selectedManagedUser.status === "Active"
                  ? "bg-warning/10 hover:bg-warning/20 text-warning border-warning/20"
                  : "bg-success/10 hover:bg-success/20 text-success border-success/20"
              }`}
            >
              {selectedManagedUser.status === "Active" ? (
                <>
                  <Lock className="w-3.5 h-3.5" />
                  Suspend
                </>
              ) : (
                <>
                  <Unlock className="w-3.5 h-3.5" />
                  Activate
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleResetPassword}
              disabled={isSendingReset}
              className="bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent font-bold px-3 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <KeyRound className="w-3.5 h-3.5" />
              {isSendingReset ? "Sending..." : "Reset Password"}
            </button>

            <button
              type="button"
              onClick={() => setDeletingManagedUser(selectedManagedUser)}
              className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 font-bold px-3 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer flex items-center justify-center gap-1"
            >
              <Trash2 className="w-3.5 h-3.5 text-red-500" />
              Delete Account
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
