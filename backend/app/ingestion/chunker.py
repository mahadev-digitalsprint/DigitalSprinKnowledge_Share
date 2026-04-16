from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

import tiktoken

from app.core.parsers.base import ParsedPage

logger = logging.getLogger(__name__)


class _WhitespaceEncoding:
    _token_pattern = re.compile(r"\S+\s*")

    def encode(self, text: str) -> list[str]:
        return self._token_pattern.findall(text)

    def decode(self, tokens: list[str]) -> str:
        return "".join(tokens)


def _load_encoding():
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception as exc:
        logger.warning("Falling back to whitespace chunking because tiktoken is unavailable: %s", exc)
        return _WhitespaceEncoding()


_enc = _load_encoding()


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


def chunk_pages(
    pages: list[ParsedPage],
    doc_id: str,
    collection_id: str,
    org_id: str,
    *,
    quality: str = "fast",
    version: int = 1,
    source_path: str = "",
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
                    )
                )
                chunk_index += 1

            if end == len(tokens):
                break
            start += token_budget - token_overlap

    return chunks
