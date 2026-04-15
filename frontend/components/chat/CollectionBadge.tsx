import { Database } from "lucide-react";
import { cn } from "@/lib/cn";

type CollectionBadgeProps = {
  name: string;
  docCount?: number;
  className?: string;
};

export function CollectionBadge({ name, docCount, className }: CollectionBadgeProps) {
  return (
    <div className={cn("flex items-center gap-2 min-w-0", className)}>
      <div
        className="h-6 w-6 rounded-ds-sm flex items-center justify-center shrink-0"
        style={{
          background: "var(--bg-glass-active)",
          border: "1px solid var(--border-brand)",
        }}
      >
        <Database size={11} style={{ color: "var(--brand)" }} />
      </div>
      <div className="min-w-0">
        <span
          className="block text-ds-nav font-semibold truncate"
          style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
        >
          {name}
        </span>
        {docCount !== undefined && (
          <span className="block text-ds-xs" style={{ color: "var(--text-faint)", lineHeight: 1 }}>
            {docCount} docs
          </span>
        )}
      </div>
    </div>
  );
}
