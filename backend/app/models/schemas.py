from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ── Collections ───────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#10a37f"
    is_public: bool = True
    embedding_profile: str | None = None
    section: str = "General"


class CollectionOut(BaseModel):
    id: str
    name: str
    description: str
    doc_count: int
    color: str
    is_public: bool
    embedding_profile: str
    section: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionSummaryItem(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: datetime


class CollectionSummaryOut(BaseModel):
    collection_id: str
    collection_name: str
    tool_count: int
    document_count: int
    tools: list[CollectionSummaryItem] = Field(default_factory=list)
    documents: list[CollectionSummaryItem] = Field(default_factory=list)


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    collection_id: str
    filename: str
    file_size: int
    status: str
    quality: str
    chunk_count: int
    record_kind: str
    tool_name: str
    tool_url: str
    short_description: str
    department: str
    primary_role: str
    audience_roles: list[str] = Field(default_factory=list)
    importance_note: str
    impact_note: str
    rating: int
    created_at: datetime

    @field_validator("audience_roles", mode="before")
    @classmethod
    def parse_audience_roles(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    model_config = {"from_attributes": True}


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadAccepted(BaseModel):
    doc_id: str
    filename: str
    collection_id: str
    record_kind: str = "document"
    tool_name: str = ""
    tool_url: str = ""
    short_description: str = ""
    department: str = ""


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
    record_kind: str = "document"
    tool_url: str = ""
    short_description: str = ""


# ── SSE events (serialised as JSON in data field) ────────────────────────────

class UploadEvent(BaseModel):
    stage: str            # accepted | parsing | parsed_fast | chunking | embedding | indexing | searchable | upgraded | error
    doc_id: str
    detail: dict = Field(default_factory=dict)
