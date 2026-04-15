"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { TopBar } from "@/components/chat/TopBar";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { UploadModal } from "@/components/modal/UploadModal";
import { mockCollections } from "@/lib/mock-data";
import type { Collection, Message, Source } from "@/lib/types";
import { fetchCollections, streamChat } from "@/lib/api-client";

let msgId = 100;
const uid = () => `m${++msgId}`;

export default function ChatPage() {
  const [collections, setCollections] = useState<Collection[]>(mockCollections);
  const [messages, setMessages] = useState<Message[]>([]);
  const [modelId, setModelId] = useState("claude-sonnet-4-6");
  const [activeCollection, setActiveCollection] = useState("all");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);

  // ── Load collections from backend ──────────────────────────────────────────
  useEffect(() => {
    fetchCollections()
      .then((cols) => {
        const mapped: Collection[] = [
          { id: "all", name: "All Documents", docCount: 0, isPublic: true, color: "#10a37f" },
          ...cols.map((c) => ({
            id: c.id,
            name: c.name,
            description: c.description,
            docCount: c.doc_count,
            isPublic: c.is_public,
            color: c.color,
          })),
        ];
        setCollections(mapped);
      })
      .catch(() => {
        // backend not running — keep mock collections so UI still works
      });
  }, []);

  const activeCol = useMemo(
    () => collections.find((c) => c.id === activeCollection),
    [activeCollection, collections],
  );

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = useCallback(
    (text: string) => {
      if (isStreaming) return;

      const userMsg: Message = {
        id: uid(),
        role: "user",
        content: text,
        createdAt: new Date(),
      };
      const streamId = uid();
      const streamingMsg: Message = {
        id: streamId,
        role: "assistant",
        content: "",
        isStreaming: true,
        createdAt: new Date(),
      };

      setMessages((prev) => [...prev, userMsg, streamingMsg]);
      setIsStreaming(true);

      const history = messages
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      // Determine provider from modelId
      const provider = modelId.startsWith("claude") ? "anthropic" : "openai";

      let cancelled = false;
      abortRef.current = () => { cancelled = true; };

      (async () => {
        try {
          const stream = streamChat({
            query: text,
            collectionId: activeCollection,
            provider,
            model: modelId,
            history,
          });

          let sources: Source[] = [];
          let fullContent = "";

          for await (const event of stream) {
            if (cancelled) break;

            if (event.type === "sources") {
              sources = event.sources.map((s) => ({
                kind: "doc" as const,
                index: s.index,
                title: s.title,
                filename: s.filename,
                page: s.page,
                collection: activeCol?.name ?? "Documents",
                excerpt: s.excerpt,
                score: s.score,
              }));
            } else if (event.type === "token") {
              fullContent += event.delta;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamId ? { ...m, content: fullContent } : m,
                ),
              );
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamId
                    ? { ...m, content: fullContent, sources, model: modelId, isStreaming: false }
                    : m,
                ),
              );
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamId
                    ? { ...m, content: `Error: ${event.error}`, isStreaming: false }
                    : m,
                ),
              );
            }
          }
        } finally {
          setIsStreaming(false);
          abortRef.current = null;
        }
      })();
    },
    [activeCollection, activeCol, isStreaming, messages, modelId],
  );

  const handleExampleClick = useCallback(
    (prompt: string) => handleSend(prompt),
    [handleSend],
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--app-bg)]">
      <Sidebar
        collections={collections}
        activeCollectionId={activeCollection}
        onCollectionChange={setActiveCollection}
        onOpenUpload={() => setUploadOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          collectionName={activeCol?.name ?? "All Documents"}
          docCount={activeCol?.docCount}
          modelId={modelId}
          onModelChange={setModelId}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <MessageList
          messages={messages}
          onExampleClick={handleExampleClick}
          className="flex-1"
        />

        <ChatInput
          modelId={modelId}
          onModelChange={setModelId}
          onSend={handleSend}
          webSearchEnabled={webSearchEnabled}
          onToggleWebSearch={() => setWebSearchEnabled((v) => !v)}
          onAttach={() => setUploadOpen(true)}
          disabled={isStreaming}
        />
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
          // Refresh collection doc counts after upload
          fetchCollections()
            .then((cols) => {
              setCollections((prev) =>
                prev.map((c) => {
                  const updated = cols.find((x) => x.id === c.id);
                  return updated ? { ...c, docCount: updated.doc_count } : c;
                }),
              );
            })
            .catch(() => {});
        }}
        collectionName={activeCol?.name ?? "All Documents"}
        collections={collections}
      />
    </div>
  );
}
