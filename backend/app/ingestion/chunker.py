from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from app.core.parsers.base import ParsedPage

logger = logging.getLogger(__name__)


class _WhitespaceEncoding:
    _token_pattern = re.compile(r"\S+\s*")

    def encode(self, text: str) -> list[str]:
        return self._token_pattern.findall(text)

    def decode(self, tokens: list[str]) -> str:
        return "".join(tokens)


_enc = _WhitespaceEncoding()


@dataclass
class Chunk:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    collection_id: str = ""
    org_id: str = ""
    text: str = ""
    page: int = 1
    chunk_index: int = 0
    quality: str = "fast"
    version: int = 1
    parent_id: str | None = None
    bbox: list[float] = field(default_factory=list)
    source_path: str = ""
    tags: list[str] = field(default_factory=list)
    record_kind: str = "document"
    tool_name: str = ""
    tool_url: str = ""
    short_description: str = ""
    department: str = ""
    primary_role: str = ""
    audience_roles: list[str] = field(default_factory=list)
    importance_note: str = ""
    impact_note: str = ""
    rating: int = 0


def chunk_pages(
    pages: list[ParsedPage],
    doc_id: str,
    collection_id: str,
    org_id: str,
    *,
    quality: str = "fast",
    version: int = 1,
    source_path: str = "",
    record_kind: str = "document",
    tool_name: str = "",
    tool_url: str = "",
    short_description: str = "",
    department: str = "",
    primary_role: str = "",
    audience_roles: list[str] | None = None,
    importance_note: str = "",
    impact_note: str = "",
    rating: int = 0,
    max_tokens: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    token_budget = max_tokens or (512 if quality == "fast" else 768)
    token_overlap = overlap or (64 if quality == "fast" else 96)

    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        tokens = _enc.encode(text)
        start = 0

        while start < len(tokens):
            end = min(start + token_budget, len(tokens))
            segment = _enc.decode(tokens[start:end]).strip()
            if segment:
                chunks.append(
                    Chunk(
                        doc_id=doc_id,
                        collection_id=collection_id,
                        org_id=org_id,
                        text=segment,
                        page=page.page,
                        chunk_index=chunk_index,
                        quality=quality,
                        version=version,
                        bbox=list(page.bbox),
                        source_path=source_path,
                        tags=list(page.metadata.get("tags", [])),
                        record_kind=record_kind,
                        tool_name=tool_name,
                        tool_url=tool_url,
                        short_description=short_description,
                        department=department,
                        primary_role=primary_role,
                        audience_roles=list(audience_roles or []),
                        importance_note=importance_note,
                        impact_note=impact_note,
                        rating=rating,
                    )
                )
                chunk_index += 1

            if end == len(tokens):
                break
            start += token_budget - token_overlap

    return chunks
