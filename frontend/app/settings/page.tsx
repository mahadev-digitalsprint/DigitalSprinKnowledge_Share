"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Database, FolderKanban, MoonStar, Save, Sparkles, SunMedium } from "lucide-react";
import { Logo } from "@/components/common/Logo";
import { mockModels, mockEmbeddings } from "@/lib/mock-data";
import { CollectionOverviewPanel } from "@/components/settings/CollectionOverviewPanel";
import { fetchCollectionSummary, fetchCollections } from "@/lib/api-client";
import type { Collection, CollectionSummary } from "@/lib/types";
import { SETTINGS_STORAGE_KEY, applyTheme, isThemeMode, persistTheme, type ThemeMode } from "@/lib/theme";

const PROVIDER_COLORS: Record<string, string> = {
  openai:    "#34d399",
  azure:     "#38bdf8",
  google:    "#fb923c",
};

export default function SettingsPage() {
  const [selectedModel,     setSelectedModel]     = useState("gpt-4o");
  const [selectedEmbedding, setSelectedEmbedding] = useState("openai-large");
  const [selectedTheme, setSelectedTheme] = useState<ThemeMode>("dark");
  const [themeReady, setThemeReady] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState("all");
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
        theme?: string;
      };

      if (parsed.defaultModelId) setSelectedModel(parsed.defaultModelId);
      if (parsed.embeddingId) setSelectedEmbedding(parsed.embeddingId);
      if (isThemeMode(parsed.theme)) setSelectedTheme(parsed.theme);
    } catch {
      // Ignore invalid local settings and keep defaults.
    } finally {
      setThemeReady(true);
    }
  }, []);

  useEffect(() => {
    if (!themeReady) return;
    applyTheme(selectedTheme);
    persistTheme(selectedTheme);
  }, [selectedTheme, themeReady]);

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
        if (!cancelled) {
          setCollections([]);
        }
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
        if (!cancelled) {
          setCollectionSummary(null);
        }
      } finally {
        if (!cancelled) {
          setCollectionSummaryLoading(false);
        }
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
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        defaultModelId: selectedModel,
        embeddingId: selectedEmbedding,
        theme: selectedTheme,
      }),
    );
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div
      className="min-h-screen"
      style={{
        background: "var(--settings-page-bg)",
        backgroundAttachment: "fixed",
      }}
    >
      <header
        className="px-6 py-3.5 flex items-center justify-between sticky top-0 z-10"
        style={{
          background: "var(--header-bg)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="h-8 w-8 flex items-center justify-center rounded-ds-md transition-all duration-150"
            style={{ color: "var(--text-faint)" }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "var(--bg-glass)";
              e.currentTarget.style.color = "var(--text)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "";
              e.currentTarget.style.color = "var(--text-faint)";
            }}
          >
            <ArrowLeft size={17} />
          </Link>
          <Logo size="sm" />
        </div>

        <h1
          className="text-ds-h6 font-bold"
          style={{
            fontFamily: "Syne, system-ui, sans-serif",
            background: "var(--settings-title-gradient)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          Settings
        </h1>
        <div className="w-24" />
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <section
          className="animate-fade-in rounded-[30px] border px-6 py-6 sm:px-8"
          style={{
            borderColor: "var(--border)",
            background: "var(--hero-card-bg)",
            boxShadow: "var(--shadow-elevated)",
          }}
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--text-faint)]">
                Workspace Settings
              </p>
              <h2
                className="mt-3 text-3xl font-bold sm:text-4xl"
                style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
              >
                Tune the assistant and manage collection visibility in one place
              </h2>
              <p className="mt-3 text-sm leading-7 text-[var(--text-muted)] sm:text-base">
                I reorganized this page so the actual model settings stay together and the collection
                review lives in its own management panel. That keeps the page easier to scan and makes the
                upload overview feel deliberate instead of squeezed between controls.
              </p>
            </div>

            <button
              onClick={handleSave}
              className="inline-flex h-11 min-w-[160px] items-center justify-center gap-2 rounded-2xl px-6 text-sm font-semibold text-white transition-all duration-200 focus:outline-none"
              style={{
                background: saved
                  ? "linear-gradient(135deg, #34d399 0%, #059669 100%)"
                  : "linear-gradient(135deg, #0f8e6f 0%, #10a37f 100%)",
                boxShadow: saved
                  ? "0 0 16px rgba(52,211,153,0.35)"
                  : "0 0 18px rgba(16,163,127,0.28)",
              }}
            >
              {saved ? (
                <>
                  <Check size={15} strokeWidth={2.5} />
                  Saved!
                </>
              ) : (
                <>
                  <Save size={14} />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </section>

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <div className="space-y-6">
            <section
              className="rounded-[28px] overflow-hidden animate-fade-in"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-card)",
              }}
            >
              <div
                className="px-6 py-5 flex items-center gap-3"
                style={{ borderBottom: "1px solid var(--border)" }}
              >
                <div
                  className="h-10 w-10 rounded-2xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(16,163,127,0.12)", border: "1px solid rgba(16,163,127,0.28)" }}
                >
                  {selectedTheme === "light" ? (
                    <SunMedium size={17} style={{ color: "var(--brand)" }} />
                  ) : (
                    <MoonStar size={17} style={{ color: "var(--brand)" }} />
                  )}
                </div>
                <div>
                  <h2
                    className="text-ds-h6 font-bold"
                    style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
                  >
                    Theme
                  </h2>
                  <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    Switch between dark and light mode. The theme applies immediately across the app.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 px-6 py-5 sm:grid-cols-2">
                {([
                  {
                    id: "dark" as const,
                    title: "Dark",
                    description: "Best for focused chat sessions and low-light use.",
                    icon: <MoonStar size={16} />,
                  },
                  {
                    id: "light" as const,
                    title: "Light",
                    description: "Cleaner for daytime use and management tasks.",
                    icon: <SunMedium size={16} />,
                  },
                ] satisfies Array<{
                  id: ThemeMode;
                  title: string;
                  description: string;
                  icon: ReactNode;
                }>).map((theme) => {
                  const isSelected = theme.id === selectedTheme;
                  return (
                    <button
                      key={theme.id}
                      type="button"
                      onClick={() => setSelectedTheme(theme.id)}
                      className="rounded-[22px] border px-4 py-4 text-left transition-all duration-150"
                      style={{
                        borderColor: isSelected ? "var(--border-brand)" : "var(--border)",
                        background: isSelected ? "rgba(16,163,127,0.08)" : "var(--panel-soft-bg)",
                        boxShadow: isSelected ? "0 0 0 1px var(--border-brand)" : "none",
                      }}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div
                          className="flex h-9 w-9 items-center justify-center rounded-2xl"
                          style={{
                            background: isSelected ? "rgba(16,163,127,0.14)" : "var(--panel-ghost-bg)",
                            color: isSelected ? "var(--brand)" : "var(--text-subtle)",
                          }}
                        >
                          {theme.icon}
                        </div>
                        {isSelected && (
                          <span className="source-meta-pill" style={{ color: "var(--brand)" }}>
                            Active
                          </span>
                        )}
                      </div>
                      <p className="mt-3 text-sm font-semibold text-[var(--text-main)]">{theme.title}</p>
                      <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                        {theme.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </section>

            <section
              className="rounded-[28px] overflow-hidden animate-fade-in"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-card)",
              }}
            >
              <div
                className="px-6 py-5 flex items-center gap-3"
                style={{ borderBottom: "1px solid var(--border)" }}
              >
                <div
                  className="h-10 w-10 rounded-2xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(16,163,127,0.12)", border: "1px solid rgba(16,163,127,0.28)" }}
                >
                  <Sparkles size={17} style={{ color: "var(--brand)" }} />
                </div>
                <div>
                  <h2
                    className="text-ds-h6 font-bold"
                    style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
                  >
                    Chat Model
                  </h2>
                  <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    Choose the model that answers questions from your uploaded knowledge.
                  </p>
                </div>
              </div>

              <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {mockModels.map(model => {
                  const isSelected = model.id === selectedModel;
                  const color = PROVIDER_COLORS[model.provider] ?? "#10a37f";
                  return (
                    <label
                      key={model.id}
                      className="flex items-center gap-4 px-6 py-4 cursor-pointer transition-all duration-150"
                      style={{
                        background: isSelected ? "var(--bg-glass-active)" : "transparent",
                      }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "var(--bg-glass)"; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                    >
                      <input
                        type="radio"
                        name="model"
                        value={model.id}
                        checked={isSelected}
                        onChange={() => setSelectedModel(model.id)}
                        className="sr-only"
                      />

                      <span
                        className="h-2.5 w-2.5 rounded-full shrink-0"
                        style={{
                          backgroundColor: color,
                          boxShadow: isSelected ? `0 0 8px ${color}` : undefined,
                        }}
                      />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className="text-ds-body font-semibold"
                            style={{ color: isSelected ? color : "var(--text)" }}
                          >
                            {model.name}
                          </span>
                          {model.isFast && (
                            <span
                              className="text-ds-xs font-semibold px-2 py-0.5 rounded-full"
                              style={{ color: "var(--warning)", background: "rgba(251,146,60,0.1)", border: "1px solid rgba(251,146,60,0.2)" }}
                            >
                              Fast
                            </span>
                          )}
                          {model.isFree && (
                            <span
                              className="text-ds-xs font-semibold px-2 py-0.5 rounded-full"
                              style={{ color: "var(--success)", background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.2)" }}
                            >
                              Free
                            </span>
                          )}
                        </div>
                        <p className="text-ds-sm mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                          {model.description}
                        </p>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-ds-xs" style={{ color: "var(--text-faint)" }}>{model.contextWindow}</span>
                        <div
                          className="h-4 w-4 rounded-full border-2 flex items-center justify-center transition-all duration-150"
                          style={{
                            borderColor: isSelected ? color : "var(--border-bright)",
                            background: isSelected ? color : "transparent",
                            boxShadow: isSelected ? `0 0 8px ${color}60` : undefined,
                          }}
                        >
                          {isSelected && <Check size={9} color="white" strokeWidth={3} />}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </section>

            <section
              className="rounded-[28px] overflow-hidden animate-fade-in"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-card)",
                animationDelay: "0.08s",
              }}
            >
              <div
                className="px-6 py-5 flex items-center gap-3"
                style={{ borderBottom: "1px solid var(--border)" }}
              >
                <div
                  className="h-10 w-10 rounded-2xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(90,178,255,0.12)", border: "1px solid rgba(90,178,255,0.28)" }}
                >
                  <Database size={17} style={{ color: "var(--accent)" }} />
                </div>
                <div>
                  <h2
                    className="text-ds-h6 font-bold"
                    style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
                  >
                    Embedding Model
                  </h2>
                  <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    This controls how documents and queries are converted into vectors for retrieval.
                  </p>
                </div>
              </div>

              <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {mockEmbeddings.map(emb => {
                  const isSelected = emb.id === selectedEmbedding;
                  return (
                    <label
                      key={emb.id}
                      className="flex items-center gap-4 px-6 py-4 cursor-pointer transition-all duration-150"
                      style={{ background: isSelected ? "var(--bg-glass-active)" : "transparent" }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "var(--bg-glass)"; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                    >
                      <input
                        type="radio"
                        name="embedding"
                        value={emb.id}
                        checked={isSelected}
                        onChange={() => setSelectedEmbedding(emb.id)}
                        className="sr-only"
                      />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className="text-ds-body font-semibold"
                            style={{ color: isSelected ? "var(--accent)" : "var(--text)" }}
                          >
                            {emb.name}
                          </span>
                          <span
                            className="text-ds-xs px-1.5 py-0.5 rounded"
                            style={{ color: "var(--text-faint)", background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
                          >
                            {emb.provider}
                          </span>
                          {emb.isFree && (
                            <span
                              className="text-ds-xs font-semibold px-2 py-0.5 rounded-full"
                              style={{ color: "var(--success)", background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.2)" }}
                            >
                              Free
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 flex-wrap">
                          <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{emb.description}</p>
                          <span
                            className="text-ds-xs font-mono shrink-0 px-1.5 py-0.5 rounded"
                            style={{
                              color: "var(--accent)",
                              background: "rgba(56,189,248,0.08)",
                              border: "1px solid rgba(56,189,248,0.2)",
                            }}
                          >
                            {emb.dimensions}d
                          </span>
                        </div>
                      </div>

                      <div
                        className="h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-150"
                        style={{
                          borderColor: isSelected ? "var(--accent)" : "var(--border-bright)",
                          background: isSelected ? "var(--accent)" : "transparent",
                          boxShadow: isSelected ? "0 0 8px rgba(56,189,248,0.4)" : undefined,
                        }}
                      >
                        {isSelected && <Check size={9} color="white" strokeWidth={3} />}
                      </div>
                    </label>
                  );
                })}
              </div>
            </section>

            <section
              className="rounded-[24px] border px-5 py-4 animate-fade-in"
              style={{
                borderColor: "var(--border)",
                background: "var(--panel-soft-bg)",
                animationDelay: "0.12s",
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl"
                  style={{ background: "rgba(16,163,127,0.1)", border: "1px solid rgba(16,163,127,0.2)" }}
                >
                  <FolderKanban size={16} style={{ color: "var(--brand)" }} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--text-main)]">Why this arrangement works better</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                    Settings stay in one clean column, while collection browsing gets a dedicated workspace on
                    the right. That separation makes the page easier to understand at a glance.
                  </p>
                </div>
              </div>
            </section>
          </div>

          <div className="animate-fade-in" style={{ animationDelay: "0.05s" }}>
            <CollectionOverviewPanel
              summary={collectionSummary}
              loading={collectionSummaryLoading}
              selectedCollectionId={selectedCollectionId}
              collectionOptions={collectionOptions}
              onCollectionChange={setSelectedCollectionId}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
