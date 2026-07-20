import React from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subText: string;
  gradientClass: string;
  onClick?: () => void;
  subTextClass?: string;
  glowClass?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  subText,
  gradientClass,
  onClick,
  subTextClass = "text-white/80",
  glowClass = "",
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-gradient-to-br ${gradientClass} ${glowClass} border-none p-4 rounded-2xl flex flex-col justify-between transition-all duration-350 hover:scale-[1.03] ${
        onClick ? "cursor-pointer" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold text-white/85 uppercase tracking-wider">
          {title}
        </span>
        <span className="text-white bg-white/20 p-1.5 rounded-xl border border-white/30 backdrop-blur-xs">
          {icon}
        </span>
      </div>
      <div className="mt-4">
        <span className="text-2xl font-extrabold text-white block font-mono">
          {value}
        </span>
        <div className="flex items-center justify-between mt-1.5 text-[9px] font-bold">
          <span className={`${subTextClass} bg-white/15 px-1.5 py-0.5 rounded`}>
            {subText}
          </span>
          {onClick && (
            <span className="text-white hover:underline">
              View Details
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
