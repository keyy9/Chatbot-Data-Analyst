import React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  title: string;
  icon?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  maxWidthClass?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  title,
  icon,
  onClose,
  children,
  maxWidthClass = "max-w-md",
}) => {
  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`bg-surface border border-border w-full ${maxWidthClass} rounded-2xl shadow-2xl overflow-hidden animate-fade-in text-text`}
      >
        <div className="px-6 py-4 border-b border-border bg-surface-2/50 flex items-center justify-between">
          <h3 className="text-sm font-bold text-text uppercase tracking-wider flex items-center gap-2">
            {icon}
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body
  );
};
