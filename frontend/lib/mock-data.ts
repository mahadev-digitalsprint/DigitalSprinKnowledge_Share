import type { Collection, EmbeddingOption, Message, ModelOption, RecentChat } from "@/lib/types";

export const mockCollections: Collection[] = [
  { id: "all", name: "All Documents", docCount: 47, isPublic: true, color: "#10a37f" },
  { id: "ai-tools", name: "AI Tools", docCount: 18, isPublic: true, color: "#0ea5e9" },
  { id: "research", name: "Research Papers", docCount: 12, isPublic: true, color: "#8b5cf6" },
  { id: "meeting", name: "Meeting Notes", docCount: 9, isPublic: false, color: "#f59e0b" },
  { id: "tutorials", name: "Tutorials", docCount: 8, isPublic: true, color: "#ef4444" },
];

export const mockRecentChats: RecentChat[] = [
  { id: "c1", title: "Latest RAG stack", collectionId: "ai-tools", lastMessage: "Routing and fallback search matter more now...", updatedAt: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "c2", title: "Grounded answer UX", collectionId: "research", lastMessage: "Citation placement changes trust a lot...", updatedAt: new Date(Date.now() - 1000 * 60 * 55) },
  { id: "c3", title: "Knowledge base refresh", collectionId: "meeting", lastMessage: "Need a cleaner answer surface...", updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 4) },
  { id: "c4", title: "Retrieval eval notes", collectionId: "research", lastMessage: "Weak matches should trigger search...", updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24) },
  { id: "c5", title: "Source interaction ideas", collectionId: "tutorials", lastMessage: "Compact chips feel much lighter...", updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 40) },
];

export const mockMessages: Message[] = [
  {
    id: "m1",
    role: "user",
    content: "What changed in the latest retrieval stack for production RAG apps?",
    createdAt: new Date(Date.now() - 1000 * 60 * 10),
  },
  {
    id: "m2",
    role: "assistant",
    content: `The current production pattern is less about one framework and more about a tighter loop between retrieval, grounding, and fallback search [1][2].

The biggest change is that teams now keep the main answer surface simple while pushing retrieval quality checks and citation handling into the interaction layer [1].

1. Use a stateful orchestration layer for routing and retries [1]
2. Keep citations attached to the answer instead of detached below it [2]
3. Add web search only when the document match is weak [3]`,
    sources: [
      { kind: "doc", index: 1, title: "Production Retrieval Patterns", filename: "retrieval-patterns.pdf", page: 6, collection: "AI Tools", excerpt: "Modern RAG pipelines rely on routing, grading, and retry decisions instead of a single straight retrieval chain.", score: 0.94 },
      { kind: "doc", index: 2, title: "Answer UX Notes", filename: "answer-ux.md", page: 3, collection: "Research Papers", excerpt: "Users trust grounded answers more when the citation is visible in the answer flow and richer detail opens on demand.", score: 0.88 },
      { kind: "web", index: 3, title: "How do I search my chat history in ChatGPT?", url: "https://help.openai.com/en/articles/10056348-how-do-i-search-my-chat-history-in-chatgpt", hostname: "help.openai.com", excerpt: "ChatGPT keeps search tightly integrated with the conversation and sidebar navigation.", score: 0.79 },
    ],
    model: "gpt-4o",
    webSearched: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 9),
  },
  {
    id: "m3",
    role: "user",
    content: "Can you make the source UI cleaner too?",
    createdAt: new Date(Date.now() - 1000 * 60 * 5),
  },
  {
    id: "m4",
    role: "assistant",
    content: `Yes. The cleanest pattern is to keep sources small until the user asks for detail [1].

Inline citation pills like [1] make the answer easier to verify without turning the whole response into a wall of cards. Then a compact source strip can open one focused detail panel with the excerpt, file name, page, or domain [1][2].

That gives you a more professional reading flow and keeps the interface fast even when one answer cites several places.`,
    sources: [
      { kind: "doc", index: 1, title: "Source Interaction Review", filename: "source-interactions.pdf", page: 4, collection: "AI Tools", excerpt: "Small clickable source references preserve reading momentum better than full source cards beneath every answer.", score: 0.96 },
      { kind: "doc", index: 2, title: "Trust Signals in AI UIs", filename: "trust-signals.pdf", page: 11, collection: "AI Tools", excerpt: "Good citation UX should explain relevance, provenance, and confidence without taking over the entire layout.", score: 0.9 },
    ],
    model: "gpt-4o",
    createdAt: new Date(Date.now() - 1000 * 60 * 4),
  },
];

export const mockModels: ModelOption[] = [
  { id: "gpt-4o", provider: "openai", name: "GPT-4o", description: "Balanced reasoning and multimodal chat", contextWindow: "128K" },
  { id: "gpt-4o-mini", provider: "openai", name: "GPT-4o mini", description: "Fast and lightweight", contextWindow: "128K", isFast: true },
  { id: "claude-sonnet-4-6", provider: "anthropic", name: "Claude Sonnet 4.6", description: "Long-context reasoning", contextWindow: "200K" },
  { id: "gemini-2.0-flash", provider: "google", name: "Gemini 2.0 Flash", description: "Fast retrieval-heavy workflows", contextWindow: "1M", isFast: true },
  { id: "llama3.2", provider: "ollama", name: "Llama 3.2 (Local)", description: "Runs locally with Ollama", contextWindow: "128K", isFree: true },
];

export const mockEmbeddings: EmbeddingOption[] = [
  { id: "openai-large", provider: "OpenAI", name: "text-embedding-3-large", dimensions: 3072, description: "Best retrieval quality" },
  { id: "openai-small", provider: "OpenAI", name: "text-embedding-3-small", dimensions: 1536, description: "Good quality for lower cost" },
  { id: "cohere-en", provider: "Cohere", name: "embed-english-v3.0", dimensions: 1024, description: "Strong for RAG retrieval and reranking" },
  { id: "google", provider: "Google", name: "text-embedding-004", dimensions: 768, description: "Google embedding model" },
  { id: "nomic-local", provider: "Ollama", name: "nomic-embed-text", dimensions: 768, description: "Runs locally with no API cost", isFree: true },
];

export function formatRelativeTime(date: Date): string {
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}
