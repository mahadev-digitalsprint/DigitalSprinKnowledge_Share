"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Zap, Check } from "lucide-react";
import { cn } from "@/lib/cn";
import { mockModels } from "@/lib/mock-data";
import type { ModelOption } from "@/lib/types";

const PROVIDER_COLORS: Record<string, string> = {
  anthropic: "#a78bfa",
  openai:    "#34d399",
  azure:     "#38bdf8",
  google:    "#fb923c",
  ollama:    "#f472b6",
};

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai:    "OpenAI",
  azure:     "Azure",
  google:    "Google",
  ollama:    "Local",
};

type ModelSelectorProps = {
  value: string;
  onChange: (id: string) => void;
  compact?: boolean;
  className?: string;
};

export function ModelSelector({ value, onChange, compact = false, className }: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = mockModels.find(m => m.id === value) ?? mockModels[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  const providerColor = PROVIDER_COLORS[selected.provider] ?? "#10a37f";

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "inline-flex items-center gap-1.5 transition-all duration-150",
          "focus:outline-none rounded-ds-md",
          compact
            ? "px-2 py-1 text-ds-xs"
            : "px-3 py-1.5 text-ds-sm",
        )}
        style={{
          background: open ? "var(--surface-secondary)" : "var(--surface-primary)",
          border: `1px solid ${open ? "var(--border-strong)" : "var(--border-subtle)"}`,
          color: "var(--text-subtle)",
        }}
      >
        <span
          className="h-2 w-2 rounded-full shrink-0 animate-glow-pulse"
          style={{ backgroundColor: providerColor, boxShadow: `0 0 6px ${providerColor}` }}
          aria-hidden="true"
        />
        <span className={cn("font-medium truncate", compact ? "max-w-[90px]" : "max-w-[140px]")}>
          {compact ? selected.name.split(" ").slice(0, 2).join(" ") : selected.name}
        </span>
        {selected.isFast && !compact && (
          <Zap size={11} style={{ color: "var(--warning)", flexShrink: 0 }} />
        )}
        <ChevronDown
          size={11}
          className={cn("shrink-0 transition-transform duration-200", open && "rotate-180")}
          style={{ color: "var(--text-muted)" }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          role="listbox"
          aria-label="Select model"
          className={cn(
            "absolute z-50 rounded-ds-xl py-2 animate-scale-in",
            "min-w-[300px]",
            compact ? "bottom-full mb-2 right-0" : "top-full mt-2 right-0",
          )}
          style={{
            background: "#1b1b1d",
            border: "1px solid var(--border-subtle)",
            boxShadow: "var(--shadow-modal)",
          }}
        >
          {(["anthropic", "openai", "azure", "google", "ollama"] as const).map((provider) => {
            const providerModels = mockModels.filter(m => m.provider === provider);
            if (providerModels.length === 0) return null;

            return (
              <div key={provider}>
                <div
                  className="px-3 pt-2.5 pb-1"
                  style={{ borderTop: "1px solid var(--border-subtle)", marginTop: provider === "anthropic" ? 0 : undefined }}
                >
                  {provider !== "anthropic" && <div />}
                  <div className="flex items-center gap-1.5">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: PROVIDER_COLORS[provider] }}
                    />
                    <span
                      className="text-ds-label font-semibold uppercase tracking-widest"
                      style={{ color: "var(--text-muted)", letterSpacing: "0.08em" }}
                    >
                      {PROVIDER_LABELS[provider]}
                    </span>
                  </div>
                </div>
                {providerModels.map((model) => (
                  <ModelOptionItem
                    key={model.id}
                    model={model}
                    isSelected={model.id === value}
                    onSelect={(id) => { onChange(id); setOpen(false); }}
                    providerColor={PROVIDER_COLORS[provider] ?? "#10a37f"}
                  />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ModelOptionItem({
  model, isSelected, onSelect, providerColor,
}: {
  model: ModelOption;
  isSelected: boolean;
  onSelect: (id: string) => void;
  providerColor: string;
}) {
  return (
    <button
      role="option"
      aria-selected={isSelected}
      onClick={() => onSelect(model.id)}
      className="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-all duration-100 focus:outline-none"
      style={{
        background: isSelected ? "var(--surface-secondary)" : "transparent",
        color: isSelected ? "var(--text-main)" : "var(--text-subtle)",
      }}
    >
      <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: providerColor }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span
            className="text-ds-sm font-medium"
            style={{ color: isSelected ? providerColor : "var(--text-main)" }}
          >
            {model.name}
          </span>
          {model.isFast && <Zap size={10} style={{ color: "var(--warning)" }} />}
          {model.isFree && (
            <span
              className="text-ds-xs font-semibold px-1.5 py-0.5 rounded-full"
              style={{ color: "var(--success)", background: "rgba(52,211,153,0.12)" }}
            >
              Free
            </span>
          )}
        </div>
        <p className="text-ds-xs truncate" style={{ color: "var(--text-muted)" }}>{model.description}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-ds-xs" style={{ color: "var(--text-muted)" }}>{model.contextWindow}</span>
        {isSelected && <Check size={13} style={{ color: providerColor }} />}
      </div>
    </button>
  );
}
