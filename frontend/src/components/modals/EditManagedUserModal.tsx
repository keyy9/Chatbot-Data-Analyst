import React, { useState, useEffect } from "react";
import { Edit3 } from "lucide-react";
import { Modal } from "../Modal";
import type { ManagedUser } from "../../types/user";

type ActionResult = { success: boolean; error?: string };

interface EditManagedUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  editingManagedUser: ManagedUser | null;
  onUpdateUsername: (targetId: string, username: string) => Promise<ActionResult>;
  showToast: (msg: string) => void;
}

export const EditManagedUserModal: React.FC<EditManagedUserModalProps> = ({
  isOpen,
  onClose,
  editingManagedUser,
  onUpdateUsername,
  showToast,
}) => {
  const [editUsername, setEditUsername] = useState("");
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync state with selected user to edit
  useEffect(() => {
    if (editingManagedUser) {
      setEditUsername(editingManagedUser.username);
      setFormError("");
    }
  }, [editingManagedUser]);

  if (!editingManagedUser) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!editUsername.trim()) {
      setFormError("Username is required.");
      return;
    }

    setIsSubmitting(true);
    const res = await onUpdateUsername(editingManagedUser.id, editUsername.trim());
    setIsSubmitting(false);

    if (!res.success) {
      setFormError(res.error || "Failed to update user.");
      return;
    }

    showToast(`✏️ User account updated successfully!`);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit Managed User: ${editingManagedUser.username}`}
      icon={<Edit3 className="w-4 h-4 text-accent" />}
    >
      <form onSubmit={handleSubmit} className="font-sans">
        <div className="p-6 space-y-4">
          {formError && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-xs font-bold font-sans">
              ⚠️ {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1 font-mono">
              User ID (Read Only)
            </label>
            <input
              type="text"
              disabled
              value={editingManagedUser.id}
              className="w-full bg-surface-hover/45 border border-border text-text-muted pl-3 pr-3 py-2 rounded-lg text-sm cursor-not-allowed select-none font-mono font-bold"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1 font-mono">
              Email Address (Read Only)
            </label>
            <input
              type="text"
              disabled
              value={editingManagedUser.email}
              className="w-full bg-surface-hover/45 border border-border text-text-muted pl-3 pr-3 py-2 rounded-lg text-sm cursor-not-allowed select-none font-mono font-bold"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
              Username
            </label>
            <input
              type="text"
              required
              placeholder="e.g. elmiracinda"
              value={editUsername}
              onChange={(e) => setEditUsername(e.target.value)}
              className="w-full bg-surface-hover border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent focus:border-accent pl-3 pr-3 py-2 rounded-lg text-sm focus:outline-none transition-all font-sans"
            />
          </div>

          <div className="text-[10px] text-text-muted italic bg-surface-2/45 border border-border/60 p-3 rounded-lg leading-relaxed font-sans">
            Role isn't editable here. Use Suspend/Activate to manage account access.
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
            {isSubmitting ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
};
