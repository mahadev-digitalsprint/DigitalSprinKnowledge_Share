"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source } from "@/lib/types";

type MessageContentProps = {
  content: string;
  sources?: Source[];
  onSourceClick: (index: number) => void;
};

export function MessageContent({ content }: MessageContentProps) {
  return (
    <div className="message-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <pre className="message-code-block">{children}</pre>;
          },
          code({ className, children, ...props }) {
            const isBlock = Boolean(className);
            if (isBlock) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className="message-code-inline" {...props}>
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-lg border border-[var(--border-subtle)]">
                <table className="min-w-full text-left text-sm">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-[var(--surface-secondary)]">{children}</thead>;
          },
          th({ children }) {
            return (
              <th className="border-b border-[var(--border-subtle)] px-3 py-2 font-semibold text-[var(--text-main)]">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="border-b border-[var(--border-subtle)] px-3 py-2 align-top text-[var(--text-subtle)]">
                {children}
              </td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="message-blockquote">{children}</blockquote>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent-strong)] underline underline-offset-2 hover:opacity-80"
              >
                {children}
              </a>
            );
          },
          hr() {
            return <hr className="my-4 border-[var(--border-subtle)]" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
