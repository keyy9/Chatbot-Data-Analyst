import React, { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Modal } from "../Modal";
import type { ManagedUser } from "../../types/user";

type ActionResult = { success: boolean; error?: string };

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  deletingManagedUser: ManagedUser | null;
  onDeleteUser: (targetId: string) => Promise<ActionResult>;
  showToast: (msg: string) => void;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  deletingManagedUser,
  onDeleteUser,
  showToast,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);

  if (!deletingManagedUser) return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    const res = await onDeleteUser(deletingManagedUser.id);
    setIsDeleting(false);

    if (!res.success) {
      showToast(`⚠️ ${res.error || "Failed to delete user."}`);
      onClose();
      return;
    }

    showToast(`🗑️ User ${deletingManagedUser.username} has been deleted.`);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirm Delete User"
      icon={<AlertCircle className="w-4 h-4 text-red-500" />}
      maxWidthClass="max-w-sm"
    >
      <div className="p-6 text-center space-y-4 font-sans">
        <div className="w-12 h-12 bg-red-500/10 border border-red-500/25 text-red-500 rounded-full flex items-center justify-center mx-auto shadow-inner">
          <AlertCircle className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <p className="text-xs text-text-muted leading-relaxed font-medium">
            Are you sure you want to delete <strong className="text-text">{deletingManagedUser.username}</strong>?<br />
            This action will remove their access to the system.
          </p>
        </div>
      </div>

      <div className="px-6 py-4 border-t border-border bg-surface-2/45 flex justify-center gap-3 font-sans">
        <button
          type="button"
          onClick={onClose}
          className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text-muted font-bold px-4 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={isDeleting}
          className="bg-gradient-to-r from-red-500 to-accent-hover hover:opacity-90 text-white font-bold px-4 py-2 rounded-lg text-xs shadow-lg transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isDeleting ? "Deleting..." : "Delete User"}
        </button>
      </div>
    </Modal>
  );
};
