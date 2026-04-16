from __future__ import annotations

import logging
from functools import lru_cache

from openai import AsyncOpenAI

from app.config import settings
from app.core.http import get_async_http_client
from app.core.registry import get_embedding_profile, resolve_embedding_profile

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        http_client=get_async_http_client(),
    )


def get_embedding_dims(profile_name: str | None = None) -> int:
    return get_embedding_profile(profile_name).dimensions


def get_qdrant_collection_name(profile_name: str | None = None) -> str:
    return get_embedding_profile(profile_name).qdrant_collection


async def embed_texts(texts: list[str], profile: str | None = None) -> list[list[float]]:
    if not texts:
        return []

    resolved = resolve_embedding_profile(profile)
    cfg = get_embedding_profile(resolved)

    if cfg.provider != "openai":
        raise RuntimeError(
            f"Embedding provider '{cfg.provider}' for profile '{resolved}' is not wired yet."
        )

    client = _openai_client()
    batch_size = 512
    all_vecs: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = await client.embeddings.create(model=cfg.model, input=batch)
        all_vecs.extend(item.embedding for item in resp.data)
        logger.debug("Embedded %d/%d texts with %s", i + len(batch), len(texts), resolved)

    return all_vecs


async def embed_query(text: str, profile: str | None = None) -> list[float]:
    vectors = await embed_texts([text], profile=profile)
    return vectors[0]
