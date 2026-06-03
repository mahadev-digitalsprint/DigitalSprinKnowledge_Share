"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Database, FolderKanban, Save, Sparkles } from "lucide-react";
import { Logo } from "@/components/common/Logo";
import { mockEmbeddings, mockModels } from "@/lib/mock-data";
import { CollectionOverviewPanel } from "@/components/settings/CollectionOverviewPanel";
import { fetchCollectionSummary, fetchCollections } from "@/lib/api-client";
import type { Collection, CollectionSummary } from "@/lib/types";
import { SETTINGS_STORAGE_KEY } from "@/lib/theme";

const PROVIDER_COLORS: Record<string, string> = {
  openai: "#34d399",
  gemini: "#8ab4f8",
};

export default function SettingsPage() {
  const [selectedModel, setSelectedModel] = useState("gpt-4.1-mini");
  const [selectedEmbedding, setSelectedEmbedding] = useState("openai-small");
  const [selectedCollectionId, setSelectedCollectionId] = useState("all");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collectionSummary, setCollectionSummary] = useState<CollectionSummary | null>(null);
  const [collectionSummaryLoading, setCollectionSummaryLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as {
        defaultModelId?: string;
        embeddingId?: string;
        defaultCollectionId?: string;
      };
      if (parsed.defaultModelId) setSelectedModel(parsed.defaultModelId);
      if (parsed.embeddingId) setSelectedEmbedding(parsed.embeddingId);
      if (parsed.defaultCollectionId) setSelectedCollectionId(parsed.defaultCollectionId);
    } catch {
      // Keep defaults.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadCollections = async () => {
      try {
        const apiCollections = await fetchCollections();
        if (cancelled) return;
        const totalDocs = apiCollections.reduce((sum, collection) => sum + collection.doc_count, 0);
        setCollections([
          {
            id: "all",
            name: "All Documents",
            section: "Overview",
            docCount: totalDocs,
            isPublic: true,
            color: "#10a37f",
          },
          ...apiCollections.map((collection) => ({
            id: collection.id,
            name: collection.name,
            description: collection.description,
            section: collection.section,
            docCount: collection.doc_count,
            isPublic: collection.is_public,
            color: collection.color,
          })),
        ]);
      } catch {
        if (!cancelled) setCollections([]);
      }
    };

    loadCollections().catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadSummary = async () => {
      setCollectionSummaryLoading(true);
      try {
        const summary = await fetchCollectionSummary(selectedCollectionId);
        if (cancelled) return;
        setCollectionSummary({
          collectionId: summary.collection_id,
          collectionName: summary.collection_name,
          toolCount: summary.tool_count,
          documentCount: summary.document_count,
          tools: summary.tools.map((item) => ({
            id: item.id,
            name: item.name,
            description: item.description,
            createdAt: new Date(item.created_at),
          })),
          documents: summary.documents.map((item) => ({
            id: item.id,
            name: item.name,
            description: item.description,
            createdAt: new Date(item.created_at),
          })),
        });
      } catch {
        if (!cancelled) setCollectionSummary(null);
      } finally {
        if (!cancelled) setCollectionSummaryLoading(false);
      }
    };

    loadSummary().catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selectedCollectionId]);

  const collectionOptions = useMemo(
    () => collections.map((collection) => ({ id: collection.id, name: collection.name })),
    [collections],
  );

  const handleSave = () => {
    try {
      const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      const existing = raw ? JSON.parse(raw) as Record<string, unknown> : {};
      window.localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify({
          ...existing,
          defaultModelId: selectedModel,
          embeddingId: selectedEmbedding,
          defaultCollectionId: selectedCollectionId,
        }),
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch {
      setSaved(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--app-bg)] text-[var(--text-main)]">
      <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--topbar-bg)] px-4 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-subtle)] transition hover:bg-[var(--surface-primary)] hover:text-[var(--text-main)]"
            aria-label="Back to chat"
          >
            <ArrowLeft size={17} />
          </Link>
          <Logo size="sm" />
        </div>
        <button
          onClick={handleSave}
          className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-[var(--accent-strong)] px-4 text-sm font-semibold text-white transition hover:opacity-90"
        >
          {saved ? <Check size={14} /> : <Save size={14} />}
          {saved ? "Saved" : "Save"}
        </button>
      </header>

      <main className="mx-auto grid w-full max-w-7xl gap-5 px-4 py-5 lg:grid-cols-[420px_minmax(0,1fr)]">
        <section className="space-y-5">
          <Panel icon={<Sparkles size={17} />} title="Default Chat Model">
            <div className="space-y-2">
              {mockModels.map((model) => {
                const isSelected = model.id === selectedModel;
                const color = PROVIDER_COLORS[model.provider] ?? "var(--accent-strong)";
                return (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => setSelectedModel(model.id)}
                    className="flex w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition"
                    style={{
                      borderColor: isSelected ? color : "var(--border-subtle)",
                      background: isSelected ? "var(--bg-glass-active)" : "var(--surface-primary)",
                    }}
                  >
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-[var(--text-main)]">{model.name}</span>
                      <span className="block truncate text-xs text-[var(--text-muted)]">{model.description}</span>
                    </span>
                    <span className="text-xs text-[var(--text-muted)]">{model.contextWindow}</span>
                  </button>
                );
              })}
            </div>
          </Panel>

          <Panel icon={<Database size={17} />} title="Embedding Model">
            <div className="space-y-2">
              {mockEmbeddings.map((embedding) => {
                const isSelected = embedding.id === selectedEmbedding;
                return (
                  <button
                    key={embedding.id}
                    type="button"
                    onClick={() => setSelectedEmbedding(embedding.id)}
                    className="flex w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition"
                    style={{
                      borderColor: isSelected ? "var(--accent)" : "var(--border-subtle)",
                      background: isSelected ? "var(--bg-glass-active)" : "var(--surface-primary)",
                    }}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-[var(--text-main)]">{embedding.name}</span>
                      <span className="block truncate text-xs text-[var(--text-muted)]">{embedding.description}</span>
                    </span>
                    <span className="rounded-md border border-[var(--border-subtle)] px-2 py-1 text-xs text-[var(--text-muted)]">
                      {embedding.dimensions}d
                    </span>
                  </button>
                );
              })}
            </div>
          </Panel>

          <Panel icon={<FolderKanban size={17} />} title="Default Collection">
            <select
              value={selectedCollectionId}
              onChange={(event) => setSelectedCollectionId(event.target.value)}
              className="h-10 w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] px-3 text-sm text-[var(--text-main)] outline-none"
            >
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.name}
                </option>
              ))}
            </select>
          </Panel>
        </section>

        <CollectionOverviewPanel
          summary={collectionSummary}
          loading={collectionSummaryLoading}
          selectedCollectionId={selectedCollectionId}
          collectionOptions={collectionOptions}
          onCollectionChange={setSelectedCollectionId}
        />
      </main>
    </div>
  );
}

function Panel({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-primary)]">
      <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--bg-glass-active)] text-[var(--accent-strong)]">
          {icon}
        </div>
        <h2 className="text-sm font-semibold text-[var(--text-main)]">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}
