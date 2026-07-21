import React from "react";

interface StatusBadgeProps {
  type: "role" | "status";
  value: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  if (type === "role") {
    const isAdmin = value === "Admin";
    return (
      <span
        className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[9px] font-bold ${
          isAdmin
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
        }`}
      >
        {value}
      </span>
    );
  }

  // Otherwise, it is type === "status"
  const isActive = value === "Active";
  const isSuspended = value === "Suspended";

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold ${
        isActive
          ? "bg-success/10 text-success border border-success/20"
          : isSuspended
            ? "bg-warning/10 text-warning border border-warning/20"
            : "bg-text-faint/10 text-text-muted border border-text-faint/20"
      }`}
    >
      <span
        className={`w-1 h-1 rounded-full ${
          isActive ? "bg-success" : isSuspended ? "bg-warning" : "bg-text-faint"
        }`}
      ></span>
      {value}
    </span>
  );
};
