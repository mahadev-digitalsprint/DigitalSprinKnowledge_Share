"use client";

import { Fragment, type ReactNode } from "react";
import type { Source } from "@/lib/types";

type MessageContentProps = {
  content: string;
  sources?: Source[];
  onSourceClick: (index: number) => void;
};

function renderInline(
  text: string,
  sources: Source[] | undefined,
  onSourceClick: (index: number) => void,
) {
  const parts = text.split(/(\[\d+\])/g);

  return parts.map((part, idx) => {
    const citationMatch = part.match(/^\[(\d+)\]$/);
    if (citationMatch) {
      const sourceIndex = Number(citationMatch[1]);
      const source = sources?.find((item) => item.index === sourceIndex);
      return (
        <button
          key={`${part}-${idx}`}
          type="button"
          onClick={() => onSourceClick(sourceIndex)}
          className="citation-pill"
          aria-label={source ? `Open source ${sourceIndex}: ${source.title}` : `Open source ${sourceIndex}`}
        >
          {sourceIndex}
        </button>
      );
    }

    const inlineParts = part.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean);
    return (
      <Fragment key={`${part}-${idx}`}>
        {inlineParts.map((inlinePart, inlineIndex) => {
          if (/^`[^`]+`$/.test(inlinePart)) {
            return (
              <code key={`${inlinePart}-${inlineIndex}`} className="message-code-inline">
                {inlinePart.slice(1, -1)}
              </code>
            );
          }

          if (/^\*\*[^*]+\*\*$/.test(inlinePart)) {
            return <strong key={`${inlinePart}-${inlineIndex}`}>{inlinePart.slice(2, -2)}</strong>;
          }

          if (/^\*[^*]+\*$/.test(inlinePart)) {
            return <em key={`${inlinePart}-${inlineIndex}`}>{inlinePart.slice(1, -1)}</em>;
          }

          return <Fragment key={`${inlinePart}-${inlineIndex}`}>{inlinePart}</Fragment>;
        })}
      </Fragment>
    );
  });
}

export function MessageContent({ content, sources, onSourceClick }: MessageContentProps) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  let paragraphLines: string[] = [];
  let listItems: { ordered: boolean; text: string }[] = [];

  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    blocks.push(
      <p key={`paragraph-${blocks.length}`}>
        {renderInline(paragraphLines.join(" "), sources, onSourceClick)}
      </p>,
    );
    paragraphLines = [];
  };

  const flushList = () => {
    if (!listItems.length) return;
    const ordered = listItems[0].ordered;
    const Tag = ordered ? "ol" : "ul";
    blocks.push(
      <Tag key={`list-${blocks.length}`}>
        {listItems.map((item, index) => (
          <li key={`${item.text}-${index}`}>
            {renderInline(item.text, sources, onSourceClick)}
          </li>
        ))}
      </Tag>,
    );
    listItems = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    const unorderedMatch = trimmed.match(/^-\s+(.*)$/);

    if (!trimmed) {
      flushParagraph();
      flushList();
      return;
    }

    if (orderedMatch) {
      flushParagraph();
      listItems.push({ ordered: true, text: orderedMatch[1] });
      return;
    }

    if (unorderedMatch) {
      flushParagraph();
      listItems.push({ ordered: false, text: unorderedMatch[1] });
      return;
    }

    if (listItems.length) {
      flushList();
    }

    paragraphLines.push(trimmed);
  });

  flushParagraph();
  flushList();

  return <div className="message-content">{blocks}</div>;
}
