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
from app.ingestion.chunker import Chunk, chunk_pages
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


def _split_roles(value: str) -> list[str]:
    return [item for item in (value or "").split(",") if item]


def build_tool_record_text(document: DocumentDB) -> str:
    audience = ", ".join(_split_roles(document.audience_roles))
    lines = [
        f"Tool name: {document.tool_name}",
        f"Short description: {document.short_description}",
        f"Department: {document.department}",
        f"Primary role: {document.primary_role}",
        f"Helpful for: {audience}",
        f"Why it is important: {document.importance_note}",
        f"How it helps: {document.impact_note}",
        f"Rating: {document.rating}/5",
    ]
    if document.tool_url:
        lines.append(f"Tool link: {document.tool_url}")
    return "\n".join(line for line in lines if line.split(': ', 1)[1])


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
            tool_name = document.tool_name if document else ""
            department = document.department if document else ""
            primary_role = document.primary_role if document else ""
            audience_roles = (
                _split_roles(document.audience_roles)
                if document
                else []
            )
            record_kind = document.record_kind if document else "document"
            tool_url = document.tool_url if document else ""
            short_description = document.short_description if document else ""
            importance_note = document.importance_note if document else ""
            impact_note = document.impact_note if document else ""
            rating = document.rating if document else 0

            chunks = await asyncio.to_thread(
                chunk_pages,
                pages,
                doc_id,
                collection_id,
                org_id,
                quality="fast",
                version=1,
                source_path=source_path,
                record_kind=record_kind,
                tool_name=tool_name,
                tool_url=tool_url,
                short_description=short_description,
                department=department,
                primary_role=primary_role,
                audience_roles=audience_roles,
                importance_note=importance_note,
                impact_note=impact_note,
                rating=rating,
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
            tool_name = document.tool_name if document else ""
            department = document.department if document else ""
            primary_role = document.primary_role if document else ""
            audience_roles = (
                _split_roles(document.audience_roles)
                if document
                else []
            )
            record_kind = document.record_kind if document else "document"
            tool_url = document.tool_url if document else ""
            short_description = document.short_description if document else ""
            importance_note = document.importance_note if document else ""
            impact_note = document.impact_note if document else ""
            rating = document.rating if document else 0

            chunks = await asyncio.to_thread(
                chunk_pages,
                pages,
                doc_id,
                collection_id,
                org_id,
                quality="premium",
                version=2,
                source_path=source_path,
                record_kind=record_kind,
                tool_name=tool_name,
                tool_url=tool_url,
                short_description=short_description,
                department=department,
                primary_role=primary_role,
                audience_roles=audience_roles,
                importance_note=importance_note,
                impact_note=impact_note,
                rating=rating,
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


async def index_tool_record(
    *,
    doc_id: str,
    collection_id: str,
    org_id: str,
    qdrant_client: Any,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            collection = await session.get(CollectionDB, collection_id)
            document = await session.get(DocumentDB, doc_id)
            if document is None:
                raise RuntimeError(f"Document {doc_id} not found")

            embedding_profile = resolve_embedding_profile(
                collection.embedding_profile if collection else None
            )
            chunk = Chunk(
                doc_id=doc_id,
                collection_id=collection_id,
                org_id=org_id,
                text=build_tool_record_text(document),
                page=1,
                chunk_index=0,
                quality="tool",
                version=1,
                source_path=document.tool_url,
                tags=["tool-record"],
                record_kind=document.record_kind,
                tool_name=document.tool_name,
                tool_url=document.tool_url,
                short_description=document.short_description,
                department=document.department,
                primary_role=document.primary_role,
                audience_roles=_split_roles(document.audience_roles),
                importance_note=document.importance_note,
                impact_note=document.impact_note,
                rating=document.rating,
            )
            vectors = await embed_texts([chunk.text], profile=embedding_profile)
            await upsert_chunks(
                qdrant_client,
                [chunk],
                vectors,
                embedding_profile=embedding_profile,
            )

            await session.execute(
                update(DocumentDB)
                .where(DocumentDB.id == doc_id)
                .values(status="indexed", chunk_count=1, quality="tool")
            )
            if collection is not None:
                await session.execute(
                    update(CollectionDB)
                    .where(CollectionDB.id == collection_id)
                    .values(doc_count=CollectionDB.doc_count + 1)
                )
            await session.commit()
    except Exception:
        logger.exception("Tool indexing failed for doc %s", doc_id)
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(DocumentDB)
                .where(DocumentDB.id == doc_id)
                .values(status="error", error_msg="Failed to index tool record")
            )
            await session.commit()
        raise
