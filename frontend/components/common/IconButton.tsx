import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  variant?: "default" | "ghost";
  size?: "sm" | "md";
  className?: string;
};

export function IconButton({
  label,
  variant = "default",
  size = "md",
  className,
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex items-center justify-center rounded-ds-md transition-all duration-150",
        "focus:outline-none focus:ring-2 focus:ring-[rgba(167,139,250,0.5)] focus:ring-offset-0",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        size === "sm"
          ? "h-6 w-6 text-ds-xs"
          : "h-8 w-8 text-ds-sm",
        variant === "ghost"
          ? "bg-transparent text-[var(--text-faint)] hover:bg-[var(--bg-glass)] hover:text-[var(--text-muted)]"
          : "bg-[var(--bg-glass)] text-[var(--text-muted)] border border-[var(--border)] hover:bg-[var(--bg-glass-hover)] hover:text-[var(--text)] hover:border-[var(--border-bright)]",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
