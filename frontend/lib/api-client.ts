const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadDocumentPayload = {
  collectionId: string;
  department: string;
  toolName: string;
  toolUrl: string;
  shortDescription: string;
  primaryRole: string;
  audienceRoles: string[];
  importanceNote: string;
  impactNote: string;
  rating: number;
};

// ── Types ─────────────────────────────────────────────────────────────────────

export type ApiCollection = {
  id: string;
  name: string;
  description: string;
  doc_count: number;
  color: string;
  is_public: boolean;
  embedding_profile: string;
  section: string;
};

export type ApiCollectionSummaryItem = {
  id: string;
  name: string;
  description: string;
  created_at: string;
};

export type ApiCollectionSummary = {
  collection_id: string;
  collection_name: string;
  tool_count: number;
  document_count: number;
  tools: ApiCollectionSummaryItem[];
  documents: ApiCollectionSummaryItem[];
};

export type UploadAccepted = {
  doc_id: string;
  filename: string;
  collection_id: string;
  record_kind: string;
  tool_name: string;
  tool_url: string;
  short_description: string;
  department: string;
};

export type UploadProgressEvent = {
  stage: "parsing" | "chunking" | "embedding" | "indexing" | "searchable" | "error";
  doc_id: string;
  pages?: number;
  chunks?: number;
  error?: string;
};

export type ChatSource = {
  kind: "doc";
  index: number;
  title: string;
  filename: string;
  page: number;
  collection_id: string;
  excerpt: string;
  score: number;
  document_id: string;
  record_kind?: string;
  tool_url?: string;
  short_description?: string;
  department?: string;
  primary_role?: string;
  rating?: number;
  quality?: string;
};

export type ChatStreamEvent =
  | { type: "sources"; sources: ChatSource[] }
  | { type: "token"; delta: string }
  | { type: "done" }
  | { type: "error"; error: string };

// ── Collections ───────────────────────────────────────────────────────────────

export async function fetchCollections(): Promise<ApiCollection[]> {
  const res = await fetch(`${API_URL}/api/collections`);
  if (!res.ok) throw new Error(`Failed to load collections: ${res.status}`);
  return res.json();
}

export async function createCollection(body: {
  name: string;
  description?: string;
  color?: string;
}): Promise<ApiCollection> {
  const res = await fetch(`${API_URL}/api/collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create collection: ${res.status}`);
  return res.json();
}

export async function fetchCollectionSummary(
  collectionId: string,
): Promise<ApiCollectionSummary> {
  const res = await fetch(`${API_URL}/api/collections/${collectionId}/summary`);
  if (!res.ok) throw new Error(`Failed to load collection summary: ${res.status}`);
  return res.json();
}

// ── Upload ────────────────────────────────────────────────────────────────────

export async function uploadDocument(
  file: File | null,
  payload: UploadDocumentPayload,
): Promise<UploadAccepted> {
  const form = new FormData();
  if (file) form.append("file", file);
  form.append("collection_id", payload.collectionId);
  form.append("department", payload.department);
  form.append("tool_name", payload.toolName);
  form.append("tool_url", payload.toolUrl);
  form.append("short_description", payload.shortDescription);
  form.append("primary_role", payload.primaryRole);
  form.append("audience_roles", JSON.stringify(payload.audienceRoles));
  form.append("importance_note", payload.importanceNote);
  form.append("impact_note", payload.impactNote);
  form.append("rating", String(payload.rating));

  const res = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed (${res.status}): ${text}`);
  }
  return res.json();
}

export function watchUploadEvents(
  docId: string,
  onEvent: (e: UploadProgressEvent) => void,
  onComplete: () => void,
  onError: (msg: string) => void,
): () => void {
  const es = new EventSource(`${API_URL}/api/events?topics=uploads&doc_id=${docId}`);

  const emit = (stage: UploadProgressEvent["stage"], data: Record<string, unknown>) => {
    onEvent({
      stage,
      doc_id: docId,
      pages: data.pages as number | undefined,
      chunks: data.chunks as number | undefined,
      error: data.error as string | undefined,
    });
  };

  const parse = (e: Event) => {
    try {
      return JSON.parse((e as MessageEvent).data) as Record<string, unknown>;
    } catch {
      return {};
    }
  };

  es.addEventListener("upload.accepted", () => {
    emit("parsing", {});
  });

  es.addEventListener("upload.parsing", () => {
    emit("parsing", {});
  });

  es.addEventListener("upload.parsed_fast", (e) => {
    emit("chunking", parse(e));
  });

  es.addEventListener("upload.embedding", (e) => {
    emit("embedding", parse(e));
  });

  es.addEventListener("upload.indexing", (e) => {
    emit("indexing", parse(e));
  });

  es.addEventListener("upload.searchable", (e) => {
    emit("searchable", parse(e));
    es.close();
    onComplete();
  });

  es.addEventListener("upload.error", (e) => {
    const data = parse(e);
    const msg = (data.error as string) ?? "Upload error";
    es.close();
    onError(msg);
  });

  return () => es.close();
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function* streamChat(params: {
  query: string;
  collectionId: string;
  provider?: string;
  model?: string;
  history?: Array<{ role: string; content: string }>;
}): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: params.query,
      collection_id: params.collectionId,
      provider: params.provider ?? "",
      model: params.model ?? "",
      history: params.history ?? [],
    }),
  });

  if (!res.ok || !res.body) {
    yield { type: "error", error: `Chat failed: ${res.status}` };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const lines = block.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const eventType = eventLine.slice(6).trim();
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(dataLine.slice(5).trim());
      } catch {
        continue;
      }

      if (eventType === "sources") {
        yield { type: "sources", sources: data as unknown as ChatSource[] };
      } else if (eventType === "token") {
        yield { type: "token", delta: (data.delta as string) ?? "" };
      } else if (eventType === "done") {
        yield { type: "done" };
        return;
      } else if (eventType === "error") {
        yield { type: "error", error: (data.error as string) ?? "Unknown error" };
        return;
      }
    }
  }
}
