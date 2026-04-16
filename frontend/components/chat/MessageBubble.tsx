"use client";

import { useState } from "react";
import { Copy, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { MessageContent } from "@/components/chat/MessageContent";
import { SourceCardList } from "@/components/chat/SourceCardList";
import type { Message } from "@/lib/types";

type MessageBubbleProps = {
  message: Message;
};

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-1 py-1">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  );
}

function AIAvatar() {
  return (
    <div className="mt-1 shrink-0">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-strong)] text-white">
        <Sparkles size={14} />
      </div>
    </div>
  );
}

function UserAvatar() {
  return (
    <div
      className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-xs font-semibold text-[var(--text-subtle)]"
    >
      U
    </div>
  );
}

function ActionBar({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="flex items-center gap-1 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
      <button title="Copy" onClick={handleCopy} className="message-action-button">
        <Copy size={12} />
      </button>
      <button
        title="Good response"
        aria-pressed={feedback === "up"}
        onClick={() => setFeedback((value) => (value === "up" ? null : "up"))}
        className="message-action-button"
        style={feedback === "up" ? { color: "var(--success)" } : undefined}
      >
        <ThumbsUp size={12} />
      </button>
      <button
        title="Bad response"
        aria-pressed={feedback === "down"}
        onClick={() => setFeedback((value) => (value === "down" ? null : "down"))}
        className="message-action-button"
        style={feedback === "down" ? { color: "var(--error)" } : undefined}
      >
        <ThumbsDown size={12} />
      </button>
      {copied && <span className="text-xs text-[var(--text-subtle)]">Copied</span>}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [activeSourceIndex, setActiveSourceIndex] = useState<number | null>(
    message.sources?.[0]?.index ?? null,
  );

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 animate-fade-in">
        <div className="flex max-w-[78%] flex-col items-end gap-1">
          <div className="rounded-[18px] border border-[var(--border-subtle)] bg-[var(--surface-secondary)] px-4 py-3 text-[15px] leading-7 text-[var(--text-main)]">
            {message.content}
          </div>
        </div>
        <UserAvatar />
      </div>
    );
  }

  return (
    <div className="group flex items-start gap-4 animate-fade-in">
      <AIAvatar />
      <div className="flex min-w-0 max-w-[86%] flex-col gap-3">
        <div className="rounded-[18px] px-1 py-0.5 text-[15px] text-[var(--text-main)]">
          {message.isStreaming ? (
            <TypingIndicator />
          ) : (
            <MessageContent
              content={message.content}
              sources={message.sources}
              onSourceClick={(index) => setActiveSourceIndex(index)}
            />
          )}
        </div>

        {!message.isStreaming && (
          <div className="flex items-center justify-between gap-2 px-1">
            <div className="flex items-center gap-2 text-xs text-[var(--text-subtle)]">
              {message.model && <span className="source-meta-pill">{message.model}</span>}
              {message.webSearched && <span className="source-meta-pill">Search</span>}
            </div>
            <ActionBar content={message.content} />
          </div>
        )}

        {message.sources && message.sources.length > 0 && !message.isStreaming && (
          <SourceCardList
            sources={message.sources}
            webSearched={message.webSearched}
            activeSourceIndex={activeSourceIndex}
          />
        )}
      </div>
    </div>
  );
}
