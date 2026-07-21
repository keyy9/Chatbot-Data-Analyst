import React, { type InputHTMLAttributes, forwardRef, useState } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { Eye, EyeOff } from "lucide-react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, type = "text", ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    const isPassword = type === "password";
    const inputType = isPassword ? (showPassword ? "text" : "password") : type;

    const handleMouseDown = (e: React.MouseEvent) => {
      e.preventDefault();
      setShowPassword(true);
    };

    const handleMouseUp = () => {
      setShowPassword(false);
    };

    const handleMouseLeave = () => {
      setShowPassword(false);
    };

    const handleTouchStart = (e: React.TouchEvent) => {
      setShowPassword(true);
    };

    const handleTouchEnd = () => {
      setShowPassword(false);
    };
    return (
      <div className="space-y-1 w-full text-left">
        {label && (
          <label className="block text-xs font-bold text-text-muted font-sans select-none">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 flex items-center justify-center text-text-faint select-none">
              {icon}
            </div>
          )}
          <input
            type={inputType}
            ref={ref}
            className={twMerge(
              clsx(
                "w-full text-sm bg-surface-2 border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent/40 focus:border-accent rounded-2xl py-2.5 focus:outline-none transition-all",
                {
                  "pl-10 pr-10": icon && isPassword,
                  "pl-10 pr-4": icon && !isPassword,
                  "pl-4 pr-10": !icon && isPassword,
                  "px-4": !icon && !isPassword,
                  "border-danger focus:border-danger focus:ring-danger/30": error,
                }
              ),
              className
            )}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              onContextMenu={(e) => e.preventDefault()}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 flex items-center justify-center text-text-faint hover:text-text transition-colors cursor-pointer select-none"
            >
              {showPassword ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
          )}
        </div>
        {error && (
          <p className="text-[10px] text-danger font-semibold mt-1 font-sans select-none">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
