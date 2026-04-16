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
  documentId?: string;
  recordKind?: "document" | "tool";
  toolUrl?: string;
  shortDescription?: string;
  department?: string;
  primaryRole?: string;
  rating?: number;
  quality?: string;
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
  section?: string;
  docCount: number;
  isPublic: boolean;
  color?: string;
};

export type CollectionSummaryItem = {
  id: string;
  name: string;
  description?: string;
  createdAt: Date;
};

export type CollectionSummary = {
  collectionId: string;
  collectionName: string;
  toolCount: number;
  documentCount: number;
  tools: CollectionSummaryItem[];
  documents: CollectionSummaryItem[];
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

export type ModelProvider = "openai" | "azure" | "google";

export type ModelOption = {
  id: string;
  provider: ModelProvider;
  requestModel?: string;
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

export type UploadMetadata = {
  toolName: string;
  toolUrl: string;
  shortDescription: string;
  primaryRole: string;
  audienceRoles: string[];
  importanceNote: string;
  impactNote: string;
  rating: number;
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
