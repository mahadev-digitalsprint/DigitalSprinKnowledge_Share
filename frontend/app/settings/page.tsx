"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Cpu, Database, Save, Sparkles } from "lucide-react";
import { cn } from "@/lib/cn";
import { Logo } from "@/components/common/Logo";
import { mockModels, mockEmbeddings } from "@/lib/mock-data";

const PROVIDER_COLORS: Record<string, string> = {
  anthropic: "#a78bfa",
  openai:    "#34d399",
  azure:     "#38bdf8",
  google:    "#fb923c",
  ollama:    "#f472b6",
};

export default function SettingsPage() {
  const [selectedModel,     setSelectedModel]     = useState("claude-sonnet-4-6");
  const [selectedEmbedding, setSelectedEmbedding] = useState("openai-large");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)", backgroundImage: "var(--grad-bg)", backgroundAttachment: "fixed" }}>

      {/* Top nav */}
      <header
        className="px-6 py-3.5 flex items-center justify-between sticky top-0 z-10"
        style={{
          background: "rgba(10,10,15,0.85)",
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
            background: "linear-gradient(135deg, #f0eeff 0%, #9491b4 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          Settings
        </h1>
        <div className="w-24" />
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10 space-y-6">

        {/* Chat Model */}
        <section
          className="rounded-ds-2xl overflow-hidden animate-fade-in"
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
              className="h-9 w-9 rounded-ds-md flex items-center justify-center shrink-0"
              style={{ background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.25)" }}
            >
              <Sparkles size={16} style={{ color: "var(--brand)" }} />
            </div>
            <div>
              <h2
                className="text-ds-h6 font-bold"
                style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
              >
                Chat Model
              </h2>
              <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Choose the LLM used to generate answers from your documents.
              </p>
            </div>
          </div>

          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {mockModels.map(model => {
              const isSelected = model.id === selectedModel;
              const color = PROVIDER_COLORS[model.provider] ?? "#a78bfa";
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
                    <div className="flex items-center gap-2">
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
                    <p className="text-ds-sm mt-0.5 leading-relaxed" style={{ color: "var(--text-muted)" }}>
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

        {/* Embedding Model */}
        <section
          className="rounded-ds-2xl overflow-hidden animate-fade-in"
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
              className="h-9 w-9 rounded-ds-md flex items-center justify-center shrink-0"
              style={{ background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.25)" }}
            >
              <Database size={16} style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <h2
                className="text-ds-h6 font-bold"
                style={{ color: "var(--text)", fontFamily: "Syne, system-ui, sans-serif" }}
              >
                Embedding Model
              </h2>
              <p className="text-ds-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Used to convert documents and queries into vectors. Changing this requires re-indexing.
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
                    <div className="flex items-center gap-3 mt-0.5">
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

        {/* Save */}
        <div className="flex justify-end pb-8">
          <button
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-6 h-10 rounded-ds-md text-ds-nav font-semibold text-white transition-all duration-200 min-w-[140px] justify-center focus:outline-none"
            style={{
              background: saved
                ? "linear-gradient(135deg, #34d399 0%, #059669 100%)"
                : "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
              boxShadow: saved
                ? "0 0 16px rgba(52,211,153,0.35)"
                : "0 0 16px rgba(167,139,250,0.35)",
              transition: "all 0.3s ease",
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
      </main>
    </div>
  );
}
