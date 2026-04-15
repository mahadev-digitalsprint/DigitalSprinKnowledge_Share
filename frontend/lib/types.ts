// ─── Source Types ─────────────────────────────────────────────────────────────

export type DocSource = {
  kind: "doc";
  index: number;
  title: string;
  filename: string;
  page?: number;
  collection: string;
  excerpt: string;
  score?: number;
};

export type WebSource = {
  kind: "web";
  index: number;
  title: string;
  url: string;
  hostname: string;
  excerpt: string;
  score?: number;
};

export type Source = DocSource | WebSource;

// ─── Message Types ────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[];
  model?: string;
  webSearched?: boolean;
  isStreaming?: boolean;
  createdAt: Date;
};

// ─── Collection Types ─────────────────────────────────────────────────────────

export type Collection = {
  id: string;
  name: string;
  description?: string;
  docCount: number;
  isPublic: boolean;
  color?: string;
};

// ─── Recent Chat Types ────────────────────────────────────────────────────────

export type RecentChat = {
  id: string;
  title: string;
  collectionId?: string;
  lastMessage: string;
  updatedAt: Date;
};

// ─── Model Types ──────────────────────────────────────────────────────────────

export type ModelProvider = "anthropic" | "openai" | "azure" | "google" | "ollama";

export type ModelOption = {
  id: string;
  provider: ModelProvider;
  name: string;
  description: string;
  contextWindow: string;
  isFast?: boolean;
  isFree?: boolean;
};

// ─── Upload Types ─────────────────────────────────────────────────────────────

export type UploadStatus = "queued" | "uploading" | "parsing" | "done" | "error";

export type UploadFile = {
  id: string;
  file: File;
  status: UploadStatus;
  progress: number;
  errorMsg?: string;
};

// ─── Settings Types ───────────────────────────────────────────────────────────

export type EmbeddingOption = {
  id: string;
  provider: string;
  name: string;
  dimensions: number;
  description: string;
  isFree?: boolean;
};
