"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { Sparkles, BookOpen, Globe2, Database } from "lucide-react";
import type { Message } from "@/lib/types";

const EXAMPLE_PROMPTS = [
  {
    icon: <BookOpen size={15} />,
    label: "What AI tools were discussed in last week's notes?",
  },
  {
    icon: <Sparkles size={15} />,
    label: "Explain the difference between RAG and fine-tuning",
  },
  {
    icon: <Globe2 size={15} />,
    label: "Search the web and compare the latest RAG frameworks",
  },
  {
    icon: <Database size={15} />,
    label: "What's the best vector database for production RAG?",
  },
];

type MessageListProps = {
  messages: Message[];
  onExampleClick: (prompt: string) => void;
  className?: string;
};

export function MessageList({ messages, onExampleClick, className }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-1 flex-col items-center justify-center px-6 py-12 text-center",
          className,
        )}
      >
        <div className="mb-10">
          <div
            className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[var(--accent-strong)] shadow-[0_20px_60px_rgba(0,0,0,0.28)]"
          >
            <Sparkles size={20} />
          </div>

          <h2 className="mb-2 text-3xl font-semibold tracking-tight text-[var(--text-main)]">
            Ask your knowledge base
          </h2>
          <p className="max-w-xl text-[15px] leading-7 text-[var(--text-subtle)]">
            Answers stay clean, citations stay close, and source details open only when you need them.
          </p>
        </div>

        <div className="grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
          {EXAMPLE_PROMPTS.map(({ icon, label }) => (
            <button
              key={label}
              onClick={() => onExampleClick(label)}
              className="flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-primary)] px-4 py-4 text-left text-[var(--text-subtle)] transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-main)] focus:outline-none"
            >
              <span className="mt-0.5 shrink-0 text-[var(--accent-strong)]">
                {icon}
              </span>
              <span className="text-sm font-medium leading-6">{label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("scrollbar-thin flex flex-1 flex-col overflow-y-auto px-4 py-8", className)}>
      <div className="mx-auto w-full max-w-4xl space-y-8">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={bottomRef} aria-hidden="true" />
      </div>
    </div>
  );
}
