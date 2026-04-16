"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { TopBar } from "@/components/chat/TopBar";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { UploadModal } from "@/components/modal/UploadModal";
import { mockCollections, mockModels } from "@/lib/mock-data";
import type { Collection, Message, RecentChat, Source } from "@/lib/types";
import { fetchCollections, streamChat } from "@/lib/api-client";

const CHAT_STORAGE_KEY = "rag-ui-chats";
const SETTINGS_STORAGE_KEY = "rag-ui-settings";
const SUPPORTED_CHAT_PROVIDERS = new Set(["anthropic", "openai"]);

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

  return supportedModels.find((model) => model.id === "gpt-4o-mini")?.id ?? supportedModels[0].id;
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
  const [modelId, setModelId] = useState("gpt-4o-mini");
  const [activeCollection, setActiveCollection] = useState("all");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);

  const refreshCollections = useCallback(async () => {
    const apiCollections = await fetchCollections();
    const totalDocs = apiCollections.reduce((sum, collection) => sum + collection.doc_count, 0);
    setCollections([
      {
        id: "all",
        name: "All Documents",
        docCount: totalDocs,
        isPublic: true,
        color: "#10a37f",
      },
      ...apiCollections.map((collection) => ({
        id: collection.id,
        name: collection.name,
        description: collection.description,
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
      if (rawSettings) {
        const parsed = JSON.parse(rawSettings) as { defaultModelId?: string };
        setModelId(getSupportedModelId(parsed.defaultModelId));
      }

      const storedChats = reviveChats(window.localStorage.getItem(CHAT_STORAGE_KEY));
      if (storedChats.length > 0) {
        setChats(storedChats);
        setActiveChatId(storedChats[0].id);
        setActiveCollection(storedChats[0].collectionId);
      }
    } catch {
      setModelId(getSupportedModelId());
    }
  }, []);

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

  const filteredRecentChats = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return recentChats;
    return recentChats.filter((chat) => {
      const haystack = `${chat.title} ${chat.lastMessage}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [recentChats, searchQuery]);

  const handleCollectionChange = useCallback(
    (collectionId: string) => {
      setActiveCollection(collectionId);
      updateChat(activeChat.id, (chat) => ({ ...chat, collectionId }));
      setSidebarOpen(false);
    },
    [activeChat.id, updateChat],
  );

  const handleNewChat = useCallback(() => {
    setSearchOpen(false);
    setSearchQuery("");
    setWebSearchEnabled(false);

    if (activeChat.messages.length === 0) {
      updateChat(activeChat.id, (chat) => ({
        ...chat,
        title: "New chat",
        collectionId: activeCollection,
        messages: [],
        updatedAt: new Date().toISOString(),
      }));
      setSidebarOpen(false);
      return;
    }

    const newChat = createChat(activeCollection);
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
    setSidebarOpen(false);
  }, [activeChat.id, activeChat.messages.length, activeCollection, updateChat]);

  const handleOpenSearch = useCallback(() => {
    setSearchOpen(true);
    setSidebarOpen(true);
  }, []);

  const handleCloseSearch = useCallback(() => {
    setSearchOpen(false);
    setSearchQuery("");
  }, []);

  const handleSelectChat = useCallback(
    (chatId: string) => {
      const selectedChat = chats.find((chat) => chat.id === chatId);
      if (!selectedChat) return;
      setActiveChatId(chatId);
      setActiveCollection(selectedChat.collectionId);
      setSearchOpen(false);
      setSearchQuery("");
      setSidebarOpen(false);
    },
    [chats],
  );

  const handleSend = useCallback(
    (text: string) => {
      const prompt = text.trim();
      if (!prompt || isStreaming) return;

      const chatId = activeChat.id;
      const currentMessages = activeChat.messages;
      const selectedModel = mockModels.find((model) => model.id === modelId);
      const provider = selectedModel?.provider ?? "openai";
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

      if (!SUPPORTED_CHAT_PROVIDERS.has(provider)) {
        updateChat(chatId, (chat) => ({
          ...chat,
          messages: chat.messages.map((message) =>
            message.id === streamId
              ? {
                  ...message,
                  content: `${selectedModel?.name ?? modelId} is not wired to the backend yet. Pick an OpenAI or Anthropic model.`,
                  isStreaming: false,
                  model: modelId,
                  webSearched: webSearchEnabled,
                }
              : message,
          ),
        }));
        return;
      }

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
            model: modelId,
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
        collections={collections}
        recentChats={filteredRecentChats}
        activeCollectionId={activeCollection}
        activeChatId={activeChat.id}
        onCollectionChange={handleCollectionChange}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        searchOpen={searchOpen}
        searchQuery={searchQuery}
        onSearchOpen={handleOpenSearch}
        onSearchClose={handleCloseSearch}
        onSearchQueryChange={setSearchQuery}
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
          onSearchClick={handleOpenSearch}
        />

        <MessageList messages={messages} onExampleClick={handleExampleClick} className="flex-1" />

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
