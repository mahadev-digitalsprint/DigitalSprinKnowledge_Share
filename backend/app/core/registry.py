from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.config import settings


class LLMTarget(BaseModel):
    provider: str
    model: str


class EmbeddingProfile(BaseModel):
    provider: str
    model: str
    dimensions: int
    qdrant_collection: str


class RerankTarget(BaseModel):
    provider: str
    model: str


class ParserDefaults(BaseModel):
    hot: str
    cold_default: str
    cold_scanned: str


class RegistryConfig(BaseModel):
    version: str
    llms: dict[str, LLMTarget]
    embedding_defaults: dict[str, str] = Field(default_factory=dict)
    embeddings: dict[str, EmbeddingProfile]
    rerank: dict[str, RerankTarget] = Field(default_factory=dict)
    parsers: ParserDefaults


def _registry_file() -> Path:
    return Path(settings.registry_path).resolve()


@lru_cache(maxsize=1)
def _load_registry_uncached(registry_file: str, mtime_ns: int) -> RegistryConfig:
    with open(registry_file, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return RegistryConfig.model_validate(raw)


def load_registry() -> RegistryConfig:
    path = _registry_file()
    stat = path.stat()
    return _load_registry_uncached(str(path), stat.st_mtime_ns)


def reload_registry() -> RegistryConfig:
    _load_registry_uncached.cache_clear()
    return load_registry()


def get_llm_target(name: str = "chat_default") -> LLMTarget:
    registry = load_registry()
    target = registry.llms.get(name)
    if target is None:
        raise KeyError(f"Unknown llm target '{name}'")
    return target


def resolve_embedding_profile(name: str | None = None) -> str:
    registry = load_registry()
    if not name:
        return registry.embedding_defaults.get("default", "openai-large")

    alias = registry.embedding_defaults.get(name)
    return alias or name


def get_embedding_profile(name: str | None = None) -> EmbeddingProfile:
    registry = load_registry()
    resolved = resolve_embedding_profile(name)
    profile = registry.embeddings.get(resolved)
    if profile is None:
        raise KeyError(f"Unknown embedding profile '{resolved}'")
    return profile


def list_document_embedding_profiles() -> dict[str, EmbeddingProfile]:
    registry = load_registry()
    return {
        name: profile
        for name, profile in registry.embeddings.items()
        if profile.qdrant_collection.startswith("docs_")
    }
