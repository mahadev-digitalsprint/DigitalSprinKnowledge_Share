"use client";

import { useCallback, useRef, useState } from "react";
import { ArrowUp, Globe2, Paperclip } from "lucide-react";
import { cn } from "@/lib/cn";
import { ModelSelector } from "@/components/chat/ModelSelector";

type ChatInputProps = {
  modelId: string;
  onModelChange: (id: string) => void;
  onSend: (text: string) => void;
  webSearchEnabled?: boolean;
  onToggleWebSearch?: () => void;
  onAttach?: () => void;
  disabled?: boolean;
  className?: string;
};

export function ChatInput({
  modelId,
  onModelChange,
  onSend,
  webSearchEnabled = false,
  onToggleWebSearch,
  onAttach,
  disabled = false,
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    adjustHeight();
  };

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div
      className={cn("shrink-0 px-4 pb-5 pt-3", className)}
      style={{ background: "var(--composer-gradient)" }}
    >
      <div className="mx-auto max-w-4xl">
        <div
          className="flex flex-col gap-3 rounded-[26px] border px-4 py-3 transition-all duration-200"
          style={{
            background: "var(--surface-primary)",
            borderColor: focused ? "var(--border-strong)" : "var(--border-subtle)",
            boxShadow: focused ? "var(--composer-shadow-focus)" : "var(--composer-shadow)",
          }}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Ask anything about your knowledge base..."
            rows={1}
            disabled={disabled}
            className="min-h-[28px] max-h-[160px] w-full resize-none border-none bg-transparent leading-7 outline-none placeholder:transition-opacity focus:placeholder:opacity-60 disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              color: "var(--text-main)",
              fontSize: "0.96875rem",
              height: "auto",
            }}
          />

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button title="Attach file" onClick={onAttach} className="composer-tool-button">
                <Paperclip size={14} />
              </button>

              <button
                type="button"
                title="Toggle web search"
                onClick={onToggleWebSearch}
                aria-pressed={webSearchEnabled}
                className={cn(
                  "composer-tool-button w-auto gap-1.5 px-3 text-xs font-medium",
                  webSearchEnabled && "composer-tool-button-active",
                )}
              >
                <Globe2 size={14} />
                Search
              </button>

              <ModelSelector value={modelId} onChange={onModelChange} compact />
            </div>

            <button
              onClick={handleSend}
              disabled={!canSend}
              aria-label="Send message"
              className="flex h-9 w-9 items-center justify-center rounded-full transition-all duration-200 focus:outline-none"
              style={canSend
                ? { background: "var(--text-main)", color: "var(--app-bg)" }
                : { background: "var(--surface-secondary)", color: "var(--text-muted)", cursor: "not-allowed" }}
            >
              <ArrowUp size={15} strokeWidth={2.5} />
            </button>
          </div>
        </div>

        <p className="mt-2 text-center text-xs text-[var(--text-muted)]">
          AI can make mistakes. Verify important details. Shift+Enter adds a new line.
        </p>
      </div>
    </div>
  );
}
