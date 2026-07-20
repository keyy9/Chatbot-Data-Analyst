import React, { useState } from "react";
import { UserPlus } from "lucide-react";
import { Modal } from "../Modal";
import type { ManagedUser } from "../../types/user";

type ActionResult = { success: boolean; error?: string };

interface AddManagedUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  managedUsers: ManagedUser[];
  onCreateUser: (email: string, username: string, password: string) => Promise<ActionResult>;
  showToast: (msg: string) => void;
}

export const AddManagedUserModal: React.FC<AddManagedUserModalProps> = ({
  isOpen,
  onClose,
  managedUsers,
  onCreateUser,
  showToast,
}) => {
  const [addUsername, setAddUsername] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addTempPassword, setAddTempPassword] = useState("");
  const [addConfirmPassword, setAddConfirmPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!addUsername || !addEmail || !addTempPassword || !addConfirmPassword) {
      setFormError("All fields are required.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(addEmail)) {
      setFormError("Please enter a valid email address.");
      return;
    }

    const emailExists = managedUsers.some(
      (u) => u.email.toLowerCase() === addEmail.toLowerCase()
    );
    if (emailExists) {
      setFormError("A user with this email address already exists.");
      return;
    }

    if (addTempPassword.length < 8) {
      setFormError("Password must be at least 8 characters long.");
      return;
    }

    if (addTempPassword !== addConfirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    const res = await onCreateUser(addEmail, addUsername, addTempPassword);
    setIsSubmitting(false);

    if (!res.success) {
      setFormError(res.error || "Failed to create user.");
      return;
    }

    showToast(`🎉 User ${addUsername} created successfully!`);
    onClose();

    setAddUsername("");
    setAddEmail("");
    setAddTempPassword("");
    setAddConfirmPassword("");
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Managed User Account"
      icon={<UserPlus className="w-4 h-4 text-accent" />}
    >
      <form onSubmit={handleSubmit} className="font-sans">
        <div className="p-6 space-y-4">
          {formError && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-xs font-bold font-sans">
              ⚠️ {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
              Username
            </label>
            <input
              type="text"
              required
              placeholder="e.g. elmiracinda"
              value={addUsername}
              onChange={(e) => setAddUsername(e.target.value)}
              className="w-full bg-surface-hover border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-3 pr-3 py-2 rounded-lg text-sm focus:outline-none transition-all font-sans"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
              Email Address
            </label>
            <input
              type="email"
              required
              placeholder="e.g. elmira@gmail.com"
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              className="w-full bg-surface-hover border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-3 pr-3 py-2 rounded-lg text-sm focus:outline-none transition-all font-sans"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
                Temp Password
              </label>
              <input
                type="password"
                required
                placeholder="Min 8 chars"
                value={addTempPassword}
                onChange={(e) => setAddTempPassword(e.target.value)}
                className="w-full bg-surface-hover border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-3 pr-3 py-2 rounded-lg text-sm focus:outline-none transition-all font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
                Confirm Password
              </label>
              <input
                type="password"
                required
                placeholder="Repeat password"
                value={addConfirmPassword}
                onChange={(e) => setAddConfirmPassword(e.target.value)}
                className="w-full bg-surface-hover border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-3 pr-3 py-2 rounded-lg text-sm focus:outline-none transition-all font-sans"
              />
            </div>
          </div>

          <div className="text-[10px] text-text-muted italic bg-surface-2/45 border border-border/60 p-3 rounded-lg leading-relaxed mt-2 block font-sans">
            New accounts are always created with the "User" role and "Active" status.
          </div>
        </div>

        <div className="px-6 py-4 border-t border-border bg-surface-2/30 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text-muted font-bold px-4 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer font-sans"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-gradient-to-r from-accent to-teal hover:opacity-90 text-white font-bold px-5 py-2 rounded-lg text-xs shadow-lg shadow-accent/10 transition-all cursor-pointer font-sans disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Creating..." : "Create User"}
          </button>
        </div>
      </form>
    </Modal>
  );
};
