"use client";

import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { SourceCard, SourceDetail } from "@/components/chat/SourceCard";
import { cn } from "@/lib/cn";
import type { Message } from "@/lib/types";

type SourceSidebarProps = {
  open: boolean;
  message?: Message;
  activeSourceIndex?: number | null;
  onSelectSource: (index: number) => void;
  onClose: () => void;
};

export function SourceSidebar({
  open,
  message,
  activeSourceIndex,
  onSelectSource,
  onClose,
}: SourceSidebarProps) {
  const sources = message?.sources ?? [];
  const [localIndex, setLocalIndex] = useState<number | null>(activeSourceIndex ?? sources[0]?.index ?? null);

  useEffect(() => {
    setLocalIndex(activeSourceIndex ?? sources[0]?.index ?? null);
  }, [activeSourceIndex, sources]);

  const selectedSource = useMemo(
    () => sources.find((source) => source.index === localIndex) ?? sources[0],
    [localIndex, sources],
  );

  const handleSelect = (index: number) => {
    setLocalIndex(index);
    onSelectSource(index);
  };

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "source-sidebar fixed inset-y-0 right-0 z-40 flex w-full max-w-[380px] shrink-0 flex-col border-l border-[var(--border-subtle)] bg-[var(--sidebar-bg)] transition-transform duration-300 ease-out lg:relative lg:z-0",
          open ? "translate-x-0" : "translate-x-full lg:w-0 lg:max-w-0 lg:border-l-0",
        )}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-4">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--text-main)]">Sources</p>
            <p className="truncate text-xs text-[var(--text-subtle)]">
              {sources.length > 0
                ? `${sources.length} references for this answer`
                : "Open a citation to inspect the source."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="message-action-button"
            aria-label="Close sources"
          >
            <X size={14} />
          </button>
        </div>

        {sources.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--text-subtle)]">
            Select a citation to open source details here.
          </div>
        ) : (
          <div className="scrollbar-thin flex flex-1 flex-col overflow-y-auto px-4 py-4">
            <div className="flex flex-wrap gap-2">
              {sources.map((source) => (
                <SourceCard
                  key={`${source.kind}-${source.index}-${source.title}`}
                  source={source}
                  active={source.index === selectedSource?.index}
                  onClick={() => handleSelect(source.index)}
                  className="max-w-full"
                />
              ))}
            </div>

            {selectedSource && (
              <div className="mt-4">
                <SourceDetail source={selectedSource} />
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
