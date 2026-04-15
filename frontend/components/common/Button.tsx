import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "warm-sand" | "dark" | "danger";
type Size    = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
};

const variantStyles: Record<Variant, string> = {
  primary:
    "btn-glow text-white font-semibold border border-[rgba(167,139,250,0.4)]",
  "warm-sand":
    "bg-[var(--bg-glass)] text-[var(--text-muted)] border border-[var(--border)] hover:bg-[var(--bg-glass-hover)] hover:text-[var(--text)] hover:border-[var(--border-bright)]",
  secondary:
    "bg-[var(--bg-elevated)] text-[var(--text)] border border-[var(--border-bright)] hover:bg-[var(--bg-glass-hover)] hover:border-[var(--border-brand)]",
  ghost:
    "bg-transparent text-[var(--text-muted)] hover:bg-[var(--bg-glass)] hover:text-[var(--text)]",
  dark:
    "bg-[var(--bg-elevated)] text-[var(--text)] border border-[var(--border-bright)] hover:border-[var(--brand)]",
  danger:
    "bg-[rgba(248,113,113,0.12)] text-[#f87171] border border-[rgba(248,113,113,0.3)] hover:bg-[rgba(248,113,113,0.2)]",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-7  px-3   text-ds-xs  rounded-ds-md gap-1.5",
  md: "h-9  px-4   text-ds-nav rounded-ds-md gap-2",
  lg: "h-11 px-5   text-ds-body rounded-ds-lg gap-2",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  className,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all duration-200",
        "focus:outline-none focus:ring-2 focus:ring-[rgba(167,139,250,0.5)] focus:ring-offset-0",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none",
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && "w-full",
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          {children}
        </span>
      ) : children}
    </button>
  );
}
