import { Menu, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { IconButton } from "@/components/common/IconButton";
import { ModelSelector } from "@/components/chat/ModelSelector";

type TopBarProps = {
  collectionName: string;
  docCount?: number;
  modelId: string;
  onModelChange: (id: string) => void;
  onMenuClick: () => void;
  onSearchClick: () => void;
  className?: string;
};

export function TopBar({
  collectionName,
  docCount,
  modelId,
  onModelChange,
  onMenuClick,
  onSearchClick,
  className,
}: TopBarProps) {
  return (
    <header
      className={cn("flex h-14 shrink-0 items-center justify-between gap-3 px-4", className)}
      style={{
        background: "rgba(18,18,20,0.88)",
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
          onClick={onSearchClick}
          className="hidden h-8 items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 text-xs text-[var(--text-subtle)] md:inline-flex"
        >
          <Search size={13} />
          Search chats
        </button>
        <ModelSelector value={modelId} onChange={onModelChange} />
      </div>
    </header>
  );
}
