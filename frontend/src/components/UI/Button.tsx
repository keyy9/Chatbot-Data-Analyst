import React, { type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  ...props
}) => {
  return (
    <button
      disabled={disabled || isLoading}
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center font-semibold rounded-2xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer active:scale-[0.97]",
          {
            "bg-accent hover:bg-accent-hover text-white focus:ring-accent/50 shadow-sm shadow-black/20":
              variant === "primary",
            "bg-surface-2 hover:bg-surface-hover text-text border border-border focus:ring-border":
              variant === "secondary",
            "bg-danger hover:opacity-90 text-white focus:ring-danger/50 shadow-sm":
              variant === "danger",
            "bg-transparent hover:bg-surface-2 text-text-muted hover:text-text":
              variant === "ghost",
            "text-xs px-3 py-1.5": size === "sm",
            "text-sm px-4 py-2": size === "md",
            "text-base px-5 py-2.5": size === "lg",
          }
        ),
        className
      )}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg
            className="animate-spin h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Loading...
        </span>
      ) : (
        children
      )}
    </button>
  );
};
