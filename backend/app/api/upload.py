from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import QdrantDep, SessionDep
from app.config import settings
from app.core.llm import require_openai_api_key
from app.events import event_bus
from app.db import CollectionDB, DocumentDB
from app.ingestion.pipeline import (
    _DONE,
    create_progress_queue,
    get_progress_queue,
    index_tool_record,
    run_hot_pipeline,
)
from app.models.schemas import DocumentOut, UploadAccepted
from app.retrieval.qdrant import delete_by_document
from app.storage import store_upload

router = APIRouter(tags=["upload"])

ALLOWED_EXT = {"pdf", "txt", "md", "rst", "docx", "pptx", "xlsx"}


@router.post("/api/upload", response_model=UploadAccepted, status_code=202)
async def upload_document(
    file: UploadFile | None = File(None),
    collection_id: str = Form("all"),
    tool_name: str = Form(""),
    tool_url: str = Form(""),
    short_description: str = Form(""),
    department: str = Form(""),
    primary_role: str = Form(""),
    audience_roles: str = Form("[]"),
    importance_note: str = Form(""),
    impact_note: str = Form(""),
    rating: int = Form(0),
    high_accuracy: bool = Form(False),
    session: SessionDep = ...,  # type: ignore[assignment]
    qdrant: QdrantDep = ...,  # type: ignore[assignment]
) -> UploadAccepted:
    try:
        require_openai_api_key()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if collection_id == "all":
        raise HTTPException(status_code=400, detail="Upload requires a concrete collection_id")

    collection = await session.get(CollectionDB, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not tool_name.strip():
        raise HTTPException(status_code=400, detail="tool_name is required")
    if not importance_note.strip():
        raise HTTPException(status_code=400, detail="importance_note is required")
    if not impact_note.strip():
        raise HTTPException(status_code=400, detail="impact_note is required")
    if not primary_role.strip():
        raise HTTPException(status_code=400, detail="primary_role is required")
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")
    try:
        role_list = json.loads(audience_roles)
    except json.JSONDecodeError:
        role_list = [item.strip() for item in audience_roles.split(",") if item.strip()]
    if not isinstance(role_list, list) or not all(isinstance(item, str) for item in role_list):
        raise HTTPException(status_code=400, detail="audience_roles must be a string array")

    normalized_url = tool_url.strip()
    if normalized_url and not normalized_url.startswith(("http://", "https://")):
        normalized_url = f"https://{normalized_url}"
    resolved_department = department.strip() or collection.name
    cleaned_roles = sorted({item.strip() for item in role_list if item.strip()})
    has_file = file is not None and bool(file.filename)

    if has_file:
        filename = file.filename or "document"
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")
    else:
        filename = "Tool record"

    doc_id = str(uuid.uuid4())
    object_key = ""
    content = b""
    if has_file and file is not None:
        content = await file.read()
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
        status="queued" if has_file else "indexed",
        record_kind="document" if has_file else "tool",
        tool_name=tool_name.strip(),
        tool_url=normalized_url,
        short_description=short_description.strip(),
        department=resolved_department,
        primary_role=primary_role.strip(),
        audience_roles=",".join(cleaned_roles),
        importance_note=importance_note.strip(),
        impact_note=impact_note.strip(),
        rating=rating,
    )
    session.add(doc)
    await session.commit()

    if has_file:
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
    else:
        await index_tool_record(
            doc_id=doc_id,
            collection_id=collection_id,
            org_id=settings.default_org_id,
            qdrant_client=qdrant,
        )

    return UploadAccepted(
        doc_id=doc_id,
        filename=filename,
        collection_id=collection_id,
        record_kind="document" if has_file else "tool",
        tool_name=tool_name.strip(),
        tool_url=normalized_url,
        short_description=short_description.strip(),
        department=resolved_department,
    )


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


@router.delete("/api/documents/{doc_id}", status_code=204, response_class=Response)
async def delete_document(
    doc_id: str,
    session: SessionDep = ...,  # type: ignore[assignment]
    qdrant: QdrantDep = ...,  # type: ignore[assignment]
) -> Response:
    result = await session.execute(select(DocumentDB).where(DocumentDB.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_by_document(qdrant, doc_id, embedding_profile=None)
    await session.delete(doc)
    await session.commit()
    return Response(status_code=204)
