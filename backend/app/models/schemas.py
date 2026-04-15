from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


# ── Collections ───────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#10a37f"
    is_public: bool = True
    embedding_profile: str | None = None


class CollectionOut(BaseModel):
    id: str
    name: str
    description: str
    doc_count: int
    color: str
    is_public: bool
    embedding_profile: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    collection_id: str
    filename: str
    file_size: int
    status: str
    quality: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadAccepted(BaseModel):
    doc_id: str
    filename: str
    collection_id: str


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    collection_id: str = "all"
    session_id: str = ""
    provider: str = ""   # overrides default if set
    model: str = ""      # overrides default if set
    web_search: bool = False
    history: list[ChatMessage] = Field(default_factory=list)


# ── Sources ──────────────────────────────────────────────────────────────────

class DocSource(BaseModel):
    kind: str = "doc"
    index: int
    title: str
    filename: str
    page: int
    collection_id: str
    excerpt: str
    score: float
    document_id: str
    quality: str = "fast"
    version: int = 1
    bbox: list[float] = Field(default_factory=list)


# ── SSE events (serialised as JSON in data field) ────────────────────────────

class UploadEvent(BaseModel):
    stage: str            # accepted | parsing | parsed_fast | chunking | embedding | indexing | searchable | upgraded | error
    doc_id: str
    detail: dict = Field(default_factory=dict)
