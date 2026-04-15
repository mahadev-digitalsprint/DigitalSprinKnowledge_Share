"use client";

import { useEffect, useMemo, useState } from "react";
import { SourceCard, SourceDetail } from "@/components/chat/SourceCard";
import type { Source } from "@/lib/types";

type SourceCardListProps = {
  sources: Source[];
  webSearched?: boolean;
  activeSourceIndex?: number | null;
};

export function SourceCardList({ sources, webSearched, activeSourceIndex }: SourceCardListProps) {
  const [selectedIndex, setSelectedIndex] = useState<number>(activeSourceIndex ?? sources[0]?.index ?? 0);

  useEffect(() => {
    if (typeof activeSourceIndex === "number") {
      setSelectedIndex(activeSourceIndex);
    }
  }, [activeSourceIndex]);

  const activeSource = useMemo(
    () => sources.find((source) => source.index === selectedIndex) ?? sources[0],
    [selectedIndex, sources],
  );

  if (sources.length === 0) return null;

  return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2 px-1">
        <p className="text-xs font-medium text-[var(--text-subtle)]">
          Sources
        </p>
        {webSearched && (
          <span className="source-meta-pill">Web search used</span>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {sources.map((src) => (
          <SourceCard
            key={`${src.kind}-${src.index}-${src.title}`}
            source={src}
            active={src.index === activeSource?.index}
            onClick={() => setSelectedIndex(src.index)}
          />
        ))}
      </div>

      {activeSource && <SourceDetail source={activeSource} />}
    </div>
  );
}
