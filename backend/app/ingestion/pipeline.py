from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import update

from app.core.embedder import embed_texts
from app.core.parsers.registry import (
    analyze_pages,
    get_parser,
    pick_cold_parser,
    pick_hot_parser,
)
from app.core.registry import resolve_embedding_profile
from app.db import AsyncSessionLocal, CollectionDB, DocumentDB
from app.events import event_bus
from app.ingestion.chunker import chunk_pages
from app.retrieval.qdrant import delete_by_document, upsert_chunks

logger = logging.getLogger(__name__)

_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
_DONE = "__done__"


def create_progress_queue(doc_id: str) -> asyncio.Queue[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _queues[doc_id] = queue
    return queue


def get_progress_queue(doc_id: str) -> asyncio.Queue[dict[str, Any]] | None:
    return _queues.get(doc_id)


async def _publish_upload_event(
    doc_id: str,
    event_name: str,
    *,
    legacy_stage: str | None = None,
    **data: Any,
) -> None:
    payload = {"doc_id": doc_id, **data}
    await event_bus.publish("uploads", event_name, payload)

    if legacy_stage and doc_id in _queues:
        await _queues[doc_id].put({"stage": legacy_stage, **payload})


async def run_hot_pipeline(
    doc_id: str,
    filename: str,
    content: bytes,
    collection_id: str,
    org_id: str,
    qdrant_client: Any,
    *,
    high_accuracy: bool = False,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(DocumentDB).where(DocumentDB.id == doc_id).values(status="parsing")
            )
            await session.commit()

            await _publish_upload_event(doc_id, "upload.parsing", legacy_stage="parsing")

            hot_parser = pick_hot_parser()
            pages = await asyncio.to_thread(hot_parser.parse, content, filename)
            heuristics = analyze_pages(pages, filename, high_accuracy=high_accuracy)

            await _publish_upload_event(
                doc_id,
                "upload.parsed_fast",
                legacy_stage="chunking",
                parser=hot_parser.name,
                pages=heuristics.pages,
                elapsed_ms=None,
                table_density=round(heuristics.table_density, 3),
            )

            collection = await session.get(CollectionDB, collection_id)
            embedding_profile = resolve_embedding_profile(
                collection.embedding_profile if collection else None
            )

            document = await session.get(DocumentDB, doc_id)
            source_path = document.file_path if document else ""

            chunks = await asyncio.to_thread(
                chunk_pages,
                pages,
                doc_id,
                collection_id,
                org_id,
                quality="fast",
                version=1,
                source_path=source_path,
            )

            await _publish_upload_event(
                doc_id,
                "upload.embedding",
                legacy_stage="embedding",
                chunks=len(chunks),
                embedding_profile=embedding_profile,
            )

            vectors = await embed_texts([chunk.text for chunk in chunks], profile=embedding_profile)

            await _publish_upload_event(
                doc_id,
                "upload.indexing",
                legacy_stage="indexing",
                chunks=len(chunks),
            )
            await upsert_chunks(
                qdrant_client,
                chunks,
                vectors,
                embedding_profile=embedding_profile,
            )

            await session.execute(
                update(DocumentDB)
                .where(DocumentDB.id == doc_id)
                .values(status="indexed", chunk_count=len(chunks), quality="fast")
            )
            if collection is not None:
                await session.execute(
                    update(CollectionDB)
                    .where(CollectionDB.id == collection_id)
                    .values(doc_count=CollectionDB.doc_count + 1)
                )
            await session.commit()

            await _publish_upload_event(
                doc_id,
                "upload.searchable",
                legacy_stage="searchable",
                chunks=len(chunks),
            )

        cold_parser = pick_cold_parser(heuristics)
        if cold_parser is not None:
            asyncio.create_task(
                run_cold_upgrade(
                    doc_id=doc_id,
                    filename=filename,
                    content=content,
                    collection_id=collection_id,
                    org_id=org_id,
                    qdrant_client=qdrant_client,
                    parser_name=cold_parser.name,
                )
            )
    except Exception as exc:
        logger.exception("Hot pipeline failed for doc %s", doc_id)
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(DocumentDB)
                .where(DocumentDB.id == doc_id)
                .values(status="error", error_msg=str(exc)[:500])
            )
            await session.commit()
        await _publish_upload_event(
            doc_id,
            "upload.error",
            legacy_stage="error",
            error=str(exc),
        )
    finally:
        queue = _queues.get(doc_id)
        if queue is not None:
            await queue.put({"stage": _DONE})
        _queues.pop(doc_id, None)


async def run_cold_upgrade(
    *,
    doc_id: str,
    filename: str,
    content: bytes,
    collection_id: str,
    org_id: str,
    qdrant_client: Any,
    parser_name: str,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            parser = get_parser(parser_name)
            pages = await asyncio.to_thread(parser.parse, content, filename)
            collection = await session.get(CollectionDB, collection_id)
            embedding_profile = resolve_embedding_profile(
                collection.embedding_profile if collection else None
            )
            document = await session.get(DocumentDB, doc_id)
            source_path = document.file_path if document else ""

            chunks = await asyncio.to_thread(
                chunk_pages,
                pages,
                doc_id,
                collection_id,
                org_id,
                quality="premium",
                version=2,
                source_path=source_path,
            )
            vectors = await embed_texts([chunk.text for chunk in chunks], profile=embedding_profile)

            await upsert_chunks(
                qdrant_client,
                chunks,
                vectors,
                embedding_profile=embedding_profile,
            )
            await delete_by_document(
                qdrant_client,
                doc_id,
                embedding_profile=embedding_profile,
                quality="fast",
                version=1,
            )

            await session.execute(
                update(DocumentDB)
                .where(DocumentDB.id == doc_id)
                .values(status="indexed", chunk_count=len(chunks), quality="premium")
            )
            await session.commit()

            await _publish_upload_event(
                doc_id,
                "upload.upgraded",
                parser=parser_name,
                chunks=len(chunks),
            )
    except Exception:
        logger.exception("Cold upgrade failed for doc %s", doc_id)
