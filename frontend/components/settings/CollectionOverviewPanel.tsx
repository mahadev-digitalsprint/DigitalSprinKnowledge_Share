"use client";

import type { ReactNode } from "react";
import { FileText, Layers3, Wrench } from "lucide-react";
import type { CollectionSummary, CollectionSummaryItem } from "@/lib/types";

type CollectionOverviewPanelProps = {
  summary?: CollectionSummary | null;
  loading?: boolean;
  selectedCollectionId: string;
  collectionOptions: Array<{ id: string; name: string }>;
  onCollectionChange: (value: string) => void;
};

function formatSummaryDate(date: Date): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function SummaryBucket({
  title,
  count,
  items,
  emptyLabel,
  icon,
  accent,
}: {
  title: string;
  count: number;
  items: CollectionSummaryItem[];
  emptyLabel: string;
  icon: ReactNode;
  accent: string;
}) {
  return (
    <section
      className="rounded-[22px] border p-4"
      style={{
        borderColor: "var(--border)",
        background: "var(--hero-card-bg)",
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-2xl"
            style={{
              background: `${accent}18`,
              border: `1px solid ${accent}33`,
              color: accent,
            }}
          >
            {icon}
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-main)]">{title}</p>
            <p className="text-xs text-[var(--text-muted)]">{count} uploaded</p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {items.length > 0 ? (
          items.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl border px-3 py-3"
              style={{
                borderColor: "var(--border-subtle)",
                background: "var(--panel-soft-bg)",
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-main)]">{item.name}</p>
                  {item.description ? (
                    <p className="mt-1 text-xs leading-5 text-[var(--text-subtle)]">
                      {item.description}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs leading-5 text-[var(--text-faint)]">
                      No extra summary available for this item yet.
                    </p>
                  )}
                </div>
                <span
                  className="shrink-0 rounded-full border px-2 py-1 text-[11px]"
                  style={{
                    borderColor: "var(--border-subtle)",
                    color: "var(--text-muted)",
                    background: "var(--panel-ghost-bg)",
                  }}
                >
                  {formatSummaryDate(item.createdAt)}
                </span>
              </div>
            </article>
          ))
        ) : (
          <div
            className="rounded-2xl border px-4 py-5 text-sm"
            style={{
              borderColor: "var(--border-subtle)",
              background: "var(--panel-softer-bg)",
              color: "var(--text-subtle)",
            }}
          >
            {emptyLabel}
          </div>
        )}
      </div>
    </section>
  );
}

export function CollectionOverviewPanel({
  summary,
  loading = false,
  selectedCollectionId,
  collectionOptions,
  onCollectionChange,
}: CollectionOverviewPanelProps) {
  const totalRecords = (summary?.toolCount ?? 0) + (summary?.documentCount ?? 0);

  return (
    <section
      className="rounded-[28px] border"
      style={{
        borderColor: "var(--border)",
        background: "var(--panel-strong-bg)",
        boxShadow: "var(--shadow-elevated)",
      }}
    >
      <div
        className="flex flex-col gap-5 border-b px-6 py-6"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--text-faint)]">
              Collection Overview
            </p>
            <h2
              className="mt-2 text-2xl font-bold"
              style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
            >
              See what is inside each collection
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
              Use this area to browse uploaded tools and documents, and choose which collection should be
              the default scope for new chats.
            </p>
          </div>

          <div className="w-full lg:max-w-[280px]">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
              Active collection
            </label>
            <select
              value={selectedCollectionId}
              onChange={(e) => onCollectionChange(e.target.value)}
              className="w-full rounded-2xl px-4 py-3 text-sm focus:outline-none"
              style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-bright)",
                color: "var(--text)",
              }}
            >
              {collectionOptions.length > 0 ? (
                collectionOptions.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))
              ) : (
                <option value="all">All Documents</option>
              )}
            </select>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div
            className="rounded-2xl border px-4 py-4"
            style={{ borderColor: "var(--border-subtle)", background: "var(--panel-soft-bg)" }}
          >
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-faint)]">Selected</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text-main)]">
              {summary?.collectionName ?? "Loading..."}
            </p>
          </div>

          <div
            className="rounded-2xl border px-4 py-4"
            style={{ borderColor: "var(--border-subtle)", background: "rgba(16,163,127,0.07)" }}
          >
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-faint)]">Total records</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-main)]">{totalRecords}</p>
          </div>

          <div
            className="rounded-2xl border px-4 py-4"
            style={{ borderColor: "var(--border-subtle)", background: "rgba(90,178,255,0.07)" }}
          >
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-faint)]">Breakdown</p>
            <p className="mt-2 text-sm text-[var(--text-main)]">
              {summary?.toolCount ?? 0} tools and {summary?.documentCount ?? 0} docs
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        {loading ? (
          <div
            className="rounded-[22px] border px-5 py-10 text-center text-sm"
            style={{
              borderColor: "var(--border-subtle)",
              background: "var(--panel-soft-bg)",
              color: "var(--text-subtle)",
            }}
          >
            Loading the latest uploads for this collection...
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <SummaryBucket
              title="Tools"
              count={summary?.toolCount ?? 0}
              items={summary?.tools ?? []}
              emptyLabel="No tool-only entries have been saved in this collection yet."
              icon={<Wrench size={18} />}
              accent="#10a37f"
            />
            <SummaryBucket
              title="Documents"
              count={summary?.documentCount ?? 0}
              items={summary?.documents ?? []}
              emptyLabel="No supporting documents have been uploaded in this collection yet."
              icon={<FileText size={18} />}
              accent="#5ab2ff"
            />
          </div>
        )}

        <div
          className="mt-4 flex items-center gap-2 rounded-2xl border px-4 py-3 text-xs"
          style={{
            borderColor: "var(--border-subtle)",
            background: "var(--panel-softer-bg)",
            color: "var(--text-muted)",
          }}
        >
          <Layers3 size={14} />
          The panel shows the newest few items so the page stays readable while still giving a quick
          snapshot of the default collection you will use for new chats.
        </div>
      </div>
    </section>
  );
}
