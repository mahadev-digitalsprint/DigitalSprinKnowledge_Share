from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import QdrantDep, SessionDep
from app.config import settings
from app.events import event_bus
from app.db import CollectionDB, DocumentDB
from app.ingestion.pipeline import (
    _DONE,
    create_progress_queue,
    get_progress_queue,
    run_hot_pipeline,
)
from app.models.schemas import DocumentOut, UploadAccepted
from app.retrieval.qdrant import delete_by_document
from app.storage import store_upload

router = APIRouter(tags=["upload"])

ALLOWED_EXT = {"pdf", "txt", "md", "rst", "docx", "pptx", "xlsx"}


@router.post("/api/upload", response_model=UploadAccepted, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: str = Form("all"),
    high_accuracy: bool = Form(False),
    session: SessionDep = ...,  # type: ignore[assignment]
    qdrant: QdrantDep = ...,  # type: ignore[assignment]
) -> UploadAccepted:
    if collection_id == "all":
        raise HTTPException(status_code=400, detail="Upload requires a concrete collection_id")

    filename = file.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")

    collection = await session.get(CollectionDB, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    content = await file.read()
    doc_id = str(uuid.uuid4())
    object_key = f"{settings.default_org_id}/{collection_id}/{doc_id}/{filename}"

    await asyncio.to_thread(
        store_upload,
        content,
        object_key,
        file.content_type or "application/octet-stream",
    )

    doc = DocumentDB(
        id=doc_id,
        org_id=settings.default_org_id,
        collection_id=collection_id,
        filename=filename,
        file_size=len(content),
        file_path=object_key,
        status="queued",
    )
    session.add(doc)
    await session.commit()

    create_progress_queue(doc_id)
    await event_bus.publish(
        "uploads",
        "upload.accepted",
        {"doc_id": doc_id, "size": len(content), "filename": filename},
    )

    asyncio.create_task(
        run_hot_pipeline(
            doc_id=doc_id,
            filename=filename,
            content=content,
            collection_id=collection_id,
            org_id=settings.default_org_id,
            qdrant_client=qdrant,
            high_accuracy=high_accuracy,
        )
    )

    return UploadAccepted(doc_id=doc_id, filename=filename, collection_id=collection_id)


@router.get("/api/events/{doc_id}")
async def upload_events(doc_id: str) -> StreamingResponse:
    async def generate() -> AsyncGenerator[str, None]:
        for _ in range(20):
            queue = get_progress_queue(doc_id)
            if queue is not None:
                break
            yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(0.1)
        else:
            yield f"event: error\ndata: {json.dumps({'error': 'pipeline not found'})}\n\n"
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=settings.sse_heartbeat_seconds)
            except asyncio.TimeoutError:
                yield "event: heartbeat\ndata: {}\n\n"
                continue

            if event.get("stage") == _DONE:
                break

            yield f"event: progress\ndata: {json.dumps(event)}\n\n"

        yield "event: complete\ndata: {}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/documents", response_model=list[DocumentOut])
async def list_documents(
    collection_id: str = "all",
    session: SessionDep = ...,  # type: ignore[assignment]
) -> list[DocumentDB]:
    stmt = select(DocumentDB).where(DocumentDB.org_id == settings.default_org_id)
    if collection_id != "all":
        stmt = stmt.where(DocumentDB.collection_id == collection_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.delete("/api/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    session: SessionDep = ...,  # type: ignore[assignment]
    qdrant: QdrantDep = ...,  # type: ignore[assignment]
) -> None:
    result = await session.execute(select(DocumentDB).where(DocumentDB.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_by_document(qdrant, doc_id, embedding_profile=None)
    await session.delete(doc)
    await session.commit()
