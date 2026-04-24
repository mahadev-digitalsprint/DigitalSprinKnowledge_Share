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
      <span className="min-w-0 truncate text-sm font-medium">{source.title}</span>
      <span className="source-chip-index">{source.index}</span>
    </button>
  );
}

type SourceDetailProps = {
  source: Source;
};

export function SourceDetail({ source }: SourceDetailProps) {
  const isWeb = source.kind === "web";
  const docSource = source.kind === "doc" ? source : null;
  const meta = isWeb
    ? source.hostname
    : `${docSource?.filename ?? ""}${docSource?.page ? ` • p.${docSource.page}` : ""}`;
  const docKindLabel = docSource?.recordKind === "tool" ? "Tool record" : "Document source";
  const summary = docSource?.shortDescription?.trim() ?? "";

  return (
    <div className="source-detail-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-subtle)]">
            <span className="source-chip-icon" aria-hidden="true">
              {isWeb ? <Globe2 size={12} /> : <FileText size={12} />}
            </span>
            <span>{isWeb ? "Web source" : docKindLabel}</span>
          </div>
          <h4 className="text-sm font-semibold text-[var(--text-main)]">{source.title}</h4>
          <p className="text-xs text-[var(--text-subtle)]">{meta}</p>
        </div>
        {(isWeb || docSource?.toolUrl) && (
          <a
            href={isWeb ? source.url : docSource?.toolUrl}
            target="_blank"
            rel="noreferrer"
            className="source-link"
          >
            <ExternalLink size={13} />
            Open
          </a>
        )}
      </div>

      {summary && <p className="mt-3 text-sm leading-6 text-[var(--text-subtle)]">{summary}</p>}

      <p className="mt-3 text-sm leading-6 text-[var(--text-main)]">{source.excerpt}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-subtle)]">
        {!isWeb && docSource && <span className="source-meta-pill">{docSource.collection}</span>}
        {!isWeb && docSource?.department && <span className="source-meta-pill">{docSource.department}</span>}
        {!isWeb && docSource?.primaryRole && <span className="source-meta-pill">{docSource.primaryRole}</span>}
        {!isWeb && typeof docSource?.rating === "number" && docSource.rating > 0 && (
          <span className="source-meta-pill">Rated {docSource.rating}/5</span>
        )}
        {!isWeb && docSource?.quality && <span className="source-meta-pill">{docSource.quality}</span>}
        {typeof source.score === "number" && (
          <span className="source-meta-pill">Match {(source.score * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
}
