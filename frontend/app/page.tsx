"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { TopBar } from "@/components/chat/TopBar";
import { MessageList } from "@/components/chat/MessageList";
import { SourceSidebar } from "@/components/chat/SourceSidebar";
import { ChatInput } from "@/components/chat/ChatInput";
import { UploadModal } from "@/components/modal/UploadModal";
import { mockCollections, mockModels } from "@/lib/mock-data";
import type { Collection, Message, RecentChat, Source } from "@/lib/types";
import { fetchCollections, streamChat } from "@/lib/api-client";
import { applyTheme, isThemeMode, persistTheme, type ThemeMode } from "@/lib/theme";

const CHAT_STORAGE_KEY = "rag-ui-chats";
const SETTINGS_STORAGE_KEY = "rag-ui-settings";
const SUPPORTED_CHAT_PROVIDERS = new Set(["openai", "gemini"]);

let messageSeed = 100;
let chatSeed = 0;

const nextMessageId = () => `m${++messageSeed}`;
const nextChatId = () => `c${Date.now()}_${++chatSeed}`;

type StoredMessage = Omit<Message, "createdAt"> & { createdAt: string };
type ChatSession = {
  id: string;
  title: string;
  collectionId: string;
  messages: Message[];
  updatedAt: string;
};
type StoredChatSession = Omit<ChatSession, "messages"> & {
  messages: StoredMessage[];
};

const INITIAL_CHAT: ChatSession = {
  id: "draft-chat",
  title: "New chat",
  collectionId: "all",
  messages: [],
  updatedAt: "1970-01-01T00:00:00.000Z",
};

function buildChatTitle(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return "New chat";
  return normalized.length > 42 ? `${normalized.slice(0, 39)}...` : normalized;
}

function reviveChats(raw: string | null): ChatSession[] {
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as StoredChatSession[];
    return parsed.map((chat) => ({
      ...chat,
      messages: chat.messages.map((message) => ({
        ...message,
        createdAt: new Date(message.createdAt),
      })),
    }));
  } catch {
    return [];
  }
}

function serializeChats(chats: ChatSession[]): string {
  return JSON.stringify(
    chats.map((chat) => ({
      ...chat,
      messages: chat.messages.map((message) => ({
        ...message,
        createdAt: message.createdAt.toISOString(),
      })),
    })),
  );
}

function getSupportedModelId(preferred?: string): string {
  const supportedModels = mockModels.filter((model) =>
    SUPPORTED_CHAT_PROVIDERS.has(model.provider),
  );

  if (preferred && supportedModels.some((model) => model.id === preferred)) {
    return preferred;
  }

  return supportedModels[0].id;
}

function getLastMessagePreview(chat: ChatSession): string {
  const candidate = [...chat.messages].reverse().find((message) => message.content.trim());
  if (!candidate) return "No messages yet";
  return candidate.content.replace(/\s+/g, " ").trim();
}

function createChat(collectionId: string): ChatSession {
  return {
    id: nextChatId(),
    title: "New chat",
    collectionId,
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}


export default function ChatPage() {
  const [collections, setCollections] = useState<Collection[]>(mockCollections);
  const [chats, setChats] = useState<ChatSession[]>([INITIAL_CHAT]);
  const [activeChatId, setActiveChatId] = useState(INITIAL_CHAT.id);
  const [modelId, setModelId] = useState(mockModels[0]?.id ?? "gpt-4.1-mini");
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [defaultCollectionId, setDefaultCollectionId] = useState("all");
  const [activeCollection, setActiveCollection] = useState("all");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const [sourceMessageId, setSourceMessageId] = useState<string | null>(null);
  const [sourceIndex, setSourceIndex] = useState<number | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const refreshCollections = useCallback(async () => {
    const apiCollections = await fetchCollections();
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
  }, []);

  useEffect(() => {
    refreshCollections().catch(() => {
      // Keep mock collections when the backend is unavailable.
    });
  }, [refreshCollections]);

  useEffect(() => {
    try {
      const rawSettings = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      let preferredCollectionId = "all";
      if (rawSettings) {
        const parsed = JSON.parse(rawSettings) as {
          defaultModelId?: string;
          defaultCollectionId?: string;
          theme?: string;
        };
        if (isThemeMode(parsed.theme)) {
          setTheme(parsed.theme);
        }
        setModelId(getSupportedModelId(parsed.defaultModelId));
        if (parsed.defaultCollectionId) {
          preferredCollectionId = parsed.defaultCollectionId;
          setDefaultCollectionId(parsed.defaultCollectionId);
        }
      }

      const storedChats = reviveChats(window.localStorage.getItem(CHAT_STORAGE_KEY));
      if (storedChats.length > 0) {
        setChats(storedChats);
        setActiveChatId(storedChats[0].id);
        setActiveCollection(storedChats[0].collectionId);
      } else {
        setChats([
          {
            ...INITIAL_CHAT,
            collectionId: preferredCollectionId,
          },
        ]);
        setActiveCollection(preferredCollectionId);
      }
    } catch {
      setModelId(getSupportedModelId());
    }
  }, []);

  useEffect(() => {
    applyTheme(theme);
    persistTheme(theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(CHAT_STORAGE_KEY, serializeChats(chats));
  }, [chats]);

  useEffect(() => {
    if (!chats.some((chat) => chat.id === activeChatId)) {
      const fallbackChat = chats[0] ?? INITIAL_CHAT;
      setActiveChatId(fallbackChat.id);
      setActiveCollection(fallbackChat.collectionId);
    }
  }, [activeChatId, chats]);

  const updateChat = useCallback((chatId: string, updater: (chat: ChatSession) => ChatSession) => {
    setChats((prev) => prev.map((chat) => (chat.id === chatId ? updater(chat) : chat)));
  }, []);

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeChatId) ?? chats[0] ?? INITIAL_CHAT,
    [activeChatId, chats],
  );
  const messages = activeChat.messages;
  const activeCol = useMemo(
    () => collections.find((collection) => collection.id === activeCollection),
    [activeCollection, collections],
  );

  const recentChats = useMemo<RecentChat[]>(
    () =>
      chats
        .filter((chat) => chat.messages.length > 0)
        .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
        .map((chat) => ({
          id: chat.id,
          title: chat.title,
          collectionId: chat.collectionId,
          lastMessage: getLastMessagePreview(chat),
          updatedAt: new Date(chat.updatedAt),
        })),
    [chats],
  );

  const activeSourceMessage = useMemo(
    () =>
      messages.find((message) => message.id === sourceMessageId && (message.sources?.length ?? 0) > 0),
    [messages, sourceMessageId],
  );

  useEffect(() => {
    if (!sourceMessageId) return;

    if (!activeSourceMessage) {
      setSourcePanelOpen(false);
      setSourceMessageId(null);
      setSourceIndex(null);
      return;
    }

    if (sourceIndex === null) {
      setSourceIndex(activeSourceMessage.sources?.[0]?.index ?? null);
      return;
    }

    if (!activeSourceMessage.sources?.some((source) => source.index === sourceIndex)) {
      setSourceIndex(activeSourceMessage.sources?.[0]?.index ?? null);
    }
  }, [activeSourceMessage, sourceIndex, sourceMessageId]);

  const handleNewChat = useCallback(() => {
    setWebSearchEnabled(false);
    const nextCollectionId = defaultCollectionId || activeCollection;

    if (activeChat.messages.length === 0) {
      updateChat(activeChat.id, (chat) => ({
        ...chat,
        title: "New chat",
        collectionId: nextCollectionId,
        messages: [],
        updatedAt: new Date().toISOString(),
      }));
      setActiveCollection(nextCollectionId);
      setSidebarOpen(false);
      setSourcePanelOpen(false);
      return;
    }

    const newChat = createChat(nextCollectionId);
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
    setActiveCollection(nextCollectionId);
    setSidebarOpen(false);
    setSourcePanelOpen(false);
  }, [activeChat.id, activeChat.messages.length, activeCollection, defaultCollectionId, updateChat]);

  const handleSelectChat = useCallback(
    (chatId: string) => {
      const selectedChat = chats.find((chat) => chat.id === chatId);
      if (!selectedChat) return;
      setActiveChatId(chatId);
      setActiveCollection(selectedChat.collectionId);
      setSidebarOpen(false);
      setSourcePanelOpen(false);
    },
    [chats],
  );

  const handleOpenSources = useCallback((message: Message, selectedIndex?: number) => {
    const nextIndex = selectedIndex ?? message.sources?.[0]?.index ?? null;
    setSourceMessageId(message.id);
    setSourceIndex(nextIndex);
    setSourcePanelOpen(true);
  }, []);

  const handleSend = useCallback(
    (text: string) => {
      const prompt = text.trim();
      if (!prompt || isStreaming) return;

      const chatId = activeChat.id;
      const currentMessages = activeChat.messages;
      const selectedModel = mockModels.find((model) => model.id === modelId);
      const provider = selectedModel?.provider ?? "openai";
      const requestModel = selectedModel?.requestModel ?? modelId;
      const streamId = nextMessageId();
      const userMessage: Message = {
        id: nextMessageId(),
        role: "user",
        content: prompt,
        createdAt: new Date(),
      };
      const streamingMessage: Message = {
        id: streamId,
        role: "assistant",
        content: "",
        isStreaming: true,
        createdAt: new Date(),
      };
      const nextTitle =
        currentMessages.filter((message) => message.role === "user").length === 0
          ? buildChatTitle(prompt)
          : activeChat.title;

      updateChat(chatId, (chat) => ({
        ...chat,
        title: nextTitle,
        collectionId: activeCollection,
        updatedAt: new Date().toISOString(),
        messages: [...chat.messages, userMessage, streamingMessage],
      }));

      setIsStreaming(true);
      let cancelled = false;
      abortRef.current = () => {
        cancelled = true;
      };

      const history = currentMessages
        .slice(-6)
        .map((message) => ({ role: message.role, content: message.content }));

      (async () => {
        try {
          const stream = streamChat({
            query: prompt,
            collectionId: activeCollection,
            provider,
            model: requestModel,
            history,
          });

          let sources: Source[] = [];
          let fullContent = "";

          for await (const event of stream) {
            if (cancelled) break;

            if (event.type === "sources") {
              sources = event.sources.map((source) => ({
                kind: "doc" as const,
                index: source.index,
                title: source.title,
                filename: source.filename,
                page: source.page,
                documentId: source.document_id,
                recordKind: source.record_kind === "tool" ? "tool" : "document",
                toolUrl: source.tool_url,
                shortDescription: source.short_description,
                department: source.department,
                primaryRole: source.primary_role,
                rating: source.rating,
                quality: source.quality,
                collection:
                  collections.find((collection) => collection.id === source.collection_id)?.name ??
                  activeCol?.name ??
                  "Documents",
                excerpt: source.excerpt,
                score: source.score,
              }));
              continue;
            }

            if (event.type === "token") {
              fullContent += event.delta;
              updateChat(chatId, (chat) => ({
                ...chat,
                updatedAt: new Date().toISOString(),
                messages: chat.messages.map((message) =>
                  message.id === streamId ? { ...message, content: fullContent } : message,
                ),
              }));
              continue;
            }

            if (event.type === "done") {
              updateChat(chatId, (chat) => ({
                ...chat,
                updatedAt: new Date().toISOString(),
                messages: chat.messages.map((message) =>
                  message.id === streamId
                    ? {
                        ...message,
                        content: fullContent || "No response received.",
                        sources,
                        model: modelId,
                        webSearched: webSearchEnabled,
                        isStreaming: false,
                      }
                    : message,
                ),
              }));
              return;
            }

            if (event.type === "error") {
              updateChat(chatId, (chat) => ({
                ...chat,
                updatedAt: new Date().toISOString(),
                messages: chat.messages.map((message) =>
                  message.id === streamId
                    ? {
                        ...message,
                        content: `Error: ${event.error}`,
                        model: modelId,
                        webSearched: webSearchEnabled,
                        isStreaming: false,
                      }
                    : message,
                ),
              }));
              return;
            }
          }

          if (cancelled) {
            updateChat(chatId, (chat) => ({
              ...chat,
              messages: chat.messages.map((message) =>
                message.id === streamId
                  ? {
                      ...message,
                      content: fullContent || "Response stopped.",
                      sources,
                      model: modelId,
                      webSearched: webSearchEnabled,
                      isStreaming: false,
                    }
                  : message,
              ),
            }));
          }
        } finally {
          setIsStreaming(false);
          abortRef.current = null;
        }
      })();
    },
    [
      activeChat.id,
      activeChat.messages,
      activeChat.title,
      activeCol?.name,
      activeCollection,
      collections,
      isStreaming,
      modelId,
      updateChat,
      webSearchEnabled,
    ],
  );

  const handleExampleClick = useCallback((prompt: string) => handleSend(prompt), [handleSend]);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--app-bg)]">
      <Sidebar
        recentChats={recentChats}
        activeChatId={activeChat.id}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
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
          theme={theme}
          onToggleTheme={() => setTheme((value) => (value === "dark" ? "light" : "dark"))}
        />

        <MessageList
          messages={messages}
          onExampleClick={handleExampleClick}
          onOpenSources={handleOpenSources}
          activeSourceMessageId={sourcePanelOpen ? sourceMessageId : null}
          className="flex-1"
        />

        <ChatInput
          modelId={modelId}
          onModelChange={setModelId}
          onSend={handleSend}
          webSearchEnabled={webSearchEnabled}
          onToggleWebSearch={() => setWebSearchEnabled((value) => !value)}
          onAttach={() => setUploadOpen(true)}
          disabled={isStreaming}
        />
      </div>

      <SourceSidebar
        open={sourcePanelOpen}
        message={activeSourceMessage}
        activeSourceIndex={sourceIndex}
        onSelectSource={setSourceIndex}
        onClose={() => setSourcePanelOpen(false)}
      />

      <UploadModal
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
          refreshCollections().catch(() => {});
        }}
        preferredCollectionId={activeCollection}
        collections={collections}
      />
    </div>
  );
}
