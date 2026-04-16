from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.core.embedder import get_qdrant_collection_name
from app.core.registry import list_document_embedding_profiles
from app.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchRoute:
    embedding_profile: str
    org_id: str
    collection_id: str | None = None


def _build_filter(org_id: str, collection_id: str | None = None, **extra: Any) -> Filter:
    must: list[Any] = [
        FieldCondition(key="org_id", match=MatchValue(value=org_id)),
        FieldCondition(key="superseded", match=MatchValue(value=False)),
    ]

    if collection_id and collection_id != "all":
        must.append(FieldCondition(key="collection_id", match=MatchValue(value=collection_id)))

    for key, value in extra.items():
        if value is None:
            continue
        must.append(FieldCondition(key=key, match=MatchValue(value=value)))

    return Filter(must=must)


async def init_collections(client: AsyncQdrantClient) -> None:
    for profile_name, profile in list_document_embedding_profiles().items():
        collection_name = profile.qdrant_collection
        exists = await client.collection_exists(collection_name)
        if not exists:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=profile.dimensions, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection %s for %s", collection_name, profile_name)

        for field_name, field_schema in (
            ("org_id", PayloadSchemaType.KEYWORD),
            ("collection_id", PayloadSchemaType.KEYWORD),
            ("document_id", PayloadSchemaType.KEYWORD),
            ("superseded", PayloadSchemaType.BOOL),
            ("created_at", PayloadSchemaType.DATETIME),
        ):
            try:
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception:
                logger.debug("Payload index %s already exists on %s", field_name, collection_name)


async def upsert_chunks(
    client: AsyncQdrantClient,
    chunks: list[Chunk],
    vectors: list[list[float]],
    *,
    embedding_profile: str,
) -> None:
    collection_name = get_qdrant_collection_name(embedding_profile)
    created_at = datetime.now(timezone.utc).isoformat()

    points = [
        PointStruct(
            id=chunk.id,
            vector=vector,
            payload={
                "org_id": chunk.org_id,
                "collection_id": chunk.collection_id,
                "document_id": chunk.doc_id,
                "parent_id": chunk.parent_id,
                "text": chunk.text,
                "page": chunk.page,
                "bbox": chunk.bbox,
                "chunk_index": chunk.chunk_index,
                "quality": chunk.quality,
                "version": chunk.version,
                "superseded": False,
                "source_path": chunk.source_path,
                "created_at": created_at,
                "tags": chunk.tags,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    if not points:
        return

    await client.upsert(collection_name=collection_name, points=points, wait=True)
    logger.debug(
        "Upserted %d points into %s for document %s",
        len(points),
        collection_name,
        chunks[0].doc_id,
    )


async def search_routes(
    client: AsyncQdrantClient,
    routes: list[SearchRoute],
    query_vectors: dict[str, list[float]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for route in routes:
        collection_name = get_qdrant_collection_name(route.embedding_profile)
        vector = query_vectors[route.embedding_profile]
        response = await client.query_points(
            collection_name=collection_name,
            query=vector,
            query_filter=_build_filter(route.org_id, route.collection_id),
            limit=max(limit, 8),
            with_payload=True,
        )
        results.extend(
            {
                "id": str(hit.id),
                "text": hit.payload.get("text", ""),
                "page": hit.payload.get("page", 1),
                "document_id": hit.payload.get("document_id", ""),
                "collection_id": hit.payload.get("collection_id", ""),
                "score": hit.score,
                "quality": hit.payload.get("quality", "fast"),
                "version": hit.payload.get("version", 1),
                "bbox": hit.payload.get("bbox", []),
                "source_path": hit.payload.get("source_path", ""),
                "embedding_profile": route.embedding_profile,
            }
            for hit in response.points
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for item in results:
        key = (item["document_id"], item["page"], item["quality"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


async def delete_by_document(
    client: AsyncQdrantClient,
    document_id: str,
    *,
    embedding_profile: str | None = None,
    quality: str | None = None,
    version: int | None = None,
) -> None:
    profile_names = (
        [embedding_profile]
        if embedding_profile
        else list(list_document_embedding_profiles().keys())
    )

    for profile_name in profile_names:
        collection_name = get_qdrant_collection_name(profile_name)
        must: list[Any] = [FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        if quality is not None:
            must.append(FieldCondition(key="quality", match=MatchValue(value=quality)))
        if version is not None:
            must.append(FieldCondition(key="version", match=MatchValue(value=version)))
        query_filter = Filter(must=must)
        await client.delete(collection_name=collection_name, points_selector=query_filter)

    logger.info("Deleted points for document %s", document_id)
