"use client";

import { ExternalLink, FileText, Globe2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Source } from "@/lib/types";

type SourceCardProps = {
  source: Source;
  active?: boolean;
  onClick: () => void;
  className?: string;
};

export function SourceCard({ source, active = false, onClick, className }: SourceCardProps) {
  const isWeb = source.kind === "web";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "source-chip group inline-flex min-w-0 items-center gap-2 rounded-full px-3 py-1.5 text-left transition",
        active && "source-chip-active",
        className,
      )}
      aria-pressed={active}
      aria-label={`Open source ${source.index}: ${source.title}`}
    >
      <span className="source-chip-icon" aria-hidden="true">
        {isWeb ? <Globe2 size={12} /> : <FileText size={12} />}
      </span>
      <span className="min-w-0 truncate text-sm font-medium">
        {source.title}
      </span>
      <span className="source-chip-index">{source.index}</span>
    </button>
  );
}

type SourceDetailProps = {
  source: Source;
};

export function SourceDetail({ source }: SourceDetailProps) {
  const isWeb = source.kind === "web";
  const meta = isWeb
    ? source.hostname
    : `${source.filename}${source.page ? ` • p.${source.page}` : ""}`;

  return (
    <div className="source-detail-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-subtle)]">
            <span className="source-chip-icon" aria-hidden="true">
              {isWeb ? <Globe2 size={12} /> : <FileText size={12} />}
            </span>
            <span>{isWeb ? "Web source" : "Document source"}</span>
          </div>
          <h4 className="text-sm font-semibold text-[var(--text-main)]">{source.title}</h4>
          <p className="text-xs text-[var(--text-subtle)]">{meta}</p>
        </div>
        {isWeb && (
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="source-link"
          >
            <ExternalLink size={13} />
            Open
          </a>
        )}
      </div>

      <p className="mt-3 text-sm leading-6 text-[var(--text-main)]">{source.excerpt}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-subtle)]">
        {!isWeb && (
          <span className="source-meta-pill">{source.collection}</span>
        )}
        {typeof source.score === "number" && (
          <span className="source-meta-pill">Match {(source.score * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
}
