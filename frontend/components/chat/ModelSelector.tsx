"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Zap } from "lucide-react";
import { cn } from "@/lib/cn";
import { mockModels } from "@/lib/mock-data";
import type { ModelOption } from "@/lib/types";

const PROVIDER_COLORS: Record<string, string> = {
  openai: "#34d399",
  gemini: "#8ab4f8",
};

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  gemini: "Google Gemini",
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

  const selected = mockModels.find((model) => model.id === value) ?? mockModels[0];
  const selectedColor = PROVIDER_COLORS[selected.provider] ?? "var(--accent-strong)";
  const groupedModels = mockModels.reduce<Record<string, ModelOption[]>>((acc, model) => {
    acc[model.provider] ??= [];
    acc[model.provider].push(model);
    return acc;
  }, {});

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-ds-md transition-all duration-150 focus:outline-none",
          compact ? "px-2 py-1 text-ds-xs" : "px-3 py-1.5 text-ds-sm",
        )}
        style={{
          background: open ? "var(--surface-secondary)" : "var(--surface-primary)",
          border: `1px solid ${open ? "var(--border-strong)" : "var(--border-subtle)"}`,
          color: "var(--text-subtle)",
        }}
      >
        <span
          className="h-2 w-2 shrink-0 rounded-full animate-glow-pulse"
          style={{ backgroundColor: selectedColor, boxShadow: `0 0 6px ${selectedColor}` }}
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

      {open && (
        <div
          role="listbox"
          aria-label="Select model"
          className={cn(
            "absolute z-50 min-w-[300px] rounded-ds-xl py-2 animate-scale-in",
            compact ? "bottom-full right-0 mb-2" : "top-full right-0 mt-2",
          )}
          style={{
            background: "var(--surface-primary)",
            border: "1px solid var(--border-subtle)",
            boxShadow: "var(--shadow-modal)",
          }}
        >
          {Object.entries(groupedModels).map(([provider, models]) => (
            <div key={provider}>
              <div className="px-3 pt-2.5 pb-1">
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: PROVIDER_COLORS[provider] }} />
                  <span
                    className="text-ds-label font-semibold uppercase tracking-widest"
                    style={{ color: "var(--text-muted)", letterSpacing: "0.08em" }}
                  >
                    {PROVIDER_LABELS[provider] ?? provider}
                  </span>
                </div>
              </div>
              {models.map((model) => (
                <ModelOptionItem
                  key={model.id}
                  model={model}
                  color={PROVIDER_COLORS[model.provider] ?? "var(--accent-strong)"}
                  isSelected={model.id === value}
                  onSelect={(id) => {
                    onChange(id);
                    setOpen(false);
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ModelOptionItem({
  model,
  color,
  isSelected,
  onSelect,
}: {
  model: ModelOption;
  color: string;
  isSelected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      role="option"
      aria-selected={isSelected}
      onClick={() => onSelect(model.id)}
      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-all duration-100 focus:outline-none"
      style={{
        background: isSelected ? "var(--surface-secondary)" : "transparent",
        color: isSelected ? "var(--text-main)" : "var(--text-subtle)",
      }}
    >
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span
            className="text-ds-sm font-medium"
            style={{ color: isSelected ? color : "var(--text-main)" }}
          >
            {model.name}
          </span>
          {model.isFast && <Zap size={10} style={{ color: "var(--warning)" }} />}
        </div>
        <p className="truncate text-ds-xs" style={{ color: "var(--text-muted)" }}>
          {model.description}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-ds-xs" style={{ color: "var(--text-muted)" }}>
          {model.contextWindow}
        </span>
        {isSelected && <Check size={13} style={{ color }} />}
      </div>
    </button>
  );
}
