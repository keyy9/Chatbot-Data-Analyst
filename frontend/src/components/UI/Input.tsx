import React, { type InputHTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, type = "text", ...props }, ref) => {
    return (
      <div className="space-y-1 w-full text-left">
        {label && (
          <label className="block text-xs font-bold text-text-muted font-sans">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 flex items-center justify-center text-text-faint">
              {icon}
            </div>
          )}
          <input
            type={type}
            ref={ref}
            className={twMerge(
              clsx(
                "w-full text-sm bg-surface-2 border border-border text-text placeholder:text-text-faint focus:ring-2 focus:ring-accent/40 focus:border-accent rounded-2xl py-2.5 focus:outline-none transition-all",
                {
                  "pl-10 pr-4": icon,
                  "px-4": !icon,
                  "border-danger focus:border-danger focus:ring-danger/30": error,
                }
              ),
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p className="text-[10px] text-danger font-semibold mt-1 font-sans">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
