import { Menu, MoonStar, SunMedium } from "lucide-react";
import { cn } from "@/lib/cn";
import { IconButton } from "@/components/common/IconButton";
import { ModelSelector } from "@/components/chat/ModelSelector";
import type { ThemeMode } from "@/lib/theme";

type TopBarProps = {
  collectionName: string;
  docCount?: number;
  modelId: string;
  onModelChange: (id: string) => void;
  onMenuClick: () => void;
  theme: ThemeMode;
  onToggleTheme: () => void;
  className?: string;
};

export function TopBar({
  collectionName,
  docCount,
  modelId,
  onModelChange,
  onMenuClick,
  theme,
  onToggleTheme,
  className,
}: TopBarProps) {
  return (
    <header
      className={cn("flex h-14 shrink-0 items-center justify-between gap-3 px-4", className)}
      style={{
        background: "var(--topbar-bg)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <IconButton
          label="Open sidebar"
          onClick={onMenuClick}
          className="shrink-0 md:hidden"
          variant="ghost"
        >
          <Menu size={17} />
        </IconButton>

        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--text-main)]">{collectionName}</p>
          {docCount !== undefined && (
            <p className="truncate text-xs text-[var(--text-muted)]">{docCount} documents indexed</p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onToggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-subtle)] transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-primary)] hover:text-[var(--text-main)]"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          {theme === "dark" ? <SunMedium size={14} /> : <MoonStar size={14} />}
        </button>
        <ModelSelector value={modelId} onChange={onModelChange} />
      </div>
    </header>
  );
}
