import { Globe } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Collection } from "@/lib/types";

type CollectionListProps = {
  collections: Collection[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function CollectionList({ collections, activeId, onSelect }: CollectionListProps) {
  return (
    <ul className="flex flex-col gap-0.5" role="listbox" aria-label="Collections">
      {collections.map((col) => {
        const isActive = col.id === activeId;
        return (
          <li key={col.id} role="option" aria-selected={isActive}>
            <button
              onClick={() => onSelect(col.id)}
              className={cn(
                "w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-all duration-150",
                "focus:outline-none",
                isActive
                  ? "text-[var(--text-main)]"
                  : "text-[var(--text-subtle)] hover:bg-[var(--surface-primary)] hover:text-[var(--text-main)]",
              )}
              style={isActive ? {
                background: "var(--surface-primary)",
              } : undefined}
            >
              {col.id === "all" ? (
                <Globe
                  size={13}
                  className="shrink-0"
                  style={{ color: isActive ? "var(--accent-strong)" : "var(--text-muted)" }}
                />
              ) : (
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: isActive ? "var(--accent-strong)" : (col.color ?? "rgba(255,255,255,0.2)"),
                  }}
                />
              )}
              <span className="flex-1 truncate text-ds-nav font-medium">{col.name}</span>
              <span
                className="text-ds-xs tabular-nums shrink-0 px-1.5 py-0.5 rounded-full"
                style={{
                  color: isActive ? "var(--text-main)" : "var(--text-muted)",
                  background: isActive ? "rgba(255,255,255,0.06)" : "transparent",
                  fontSize: "0.65rem",
                }}
              >
                {col.docCount}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
