from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.api.deps import SessionDep
from app.config import settings
from app.core.registry import resolve_embedding_profile
from app.db import CollectionDB, DocumentDB
from app.models.schemas import (
    CollectionCreate,
    CollectionOut,
    CollectionSummaryItem,
    CollectionSummaryOut,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=list[CollectionOut])
async def list_collections(session: SessionDep) -> Sequence[CollectionDB]:
    result = await session.execute(
        select(CollectionDB).where(CollectionDB.org_id == settings.default_org_id)
    )
    return result.scalars().all()


@router.get("/{collection_id}/summary", response_model=CollectionSummaryOut)
async def get_collection_summary(
    collection_id: str,
    session: SessionDep,
) -> CollectionSummaryOut:
    if collection_id == "all":
        collection_name = "All Documents"
        stmt = (
            select(DocumentDB)
            .where(DocumentDB.org_id == settings.default_org_id)
            .order_by(DocumentDB.created_at.desc())
        )
    else:
        collection = await session.get(CollectionDB, collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        collection_name = collection.name
        stmt = (
            select(DocumentDB)
            .where(
                DocumentDB.org_id == settings.default_org_id,
                DocumentDB.collection_id == collection_id,
            )
            .order_by(DocumentDB.created_at.desc())
        )

    result = await session.execute(stmt)
    records = list(result.scalars().all())

    tools = [
        CollectionSummaryItem(
            id=record.id,
            name=record.tool_name or "Untitled tool",
            description=record.short_description or record.importance_note,
            created_at=record.created_at,
        )
        for record in records
        if record.record_kind == "tool"
    ][:5]

    documents = [
        CollectionSummaryItem(
            id=record.id,
            name=record.filename or "Untitled document",
            description=record.short_description or record.tool_name,
            created_at=record.created_at,
        )
        for record in records
        if record.record_kind != "tool"
    ][:5]

    return CollectionSummaryOut(
        collection_id=collection_id,
        collection_name=collection_name,
        tool_count=sum(1 for record in records if record.record_kind == "tool"),
        document_count=sum(1 for record in records if record.record_kind != "tool"),
        tools=tools,
        documents=documents,
    )


@router.post("", response_model=CollectionOut, status_code=201)
async def create_collection(body: CollectionCreate, session: SessionDep) -> CollectionDB:
    coll = CollectionDB(
        id=str(uuid.uuid4()),
        org_id=settings.default_org_id,
        name=body.name,
        description=body.description,
        color=body.color,
        is_public=body.is_public,
        embedding_profile=resolve_embedding_profile(body.embedding_profile),
        section=body.section,
    )
    session.add(coll)
    await session.commit()
    await session.refresh(coll)
    return coll


@router.delete("/{collection_id}", status_code=204, response_class=Response)
async def delete_collection(collection_id: str, session: SessionDep) -> Response:
    result = await session.execute(
        select(CollectionDB).where(CollectionDB.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    await session.delete(coll)
    await session.commit()
    return Response(status_code=204)
