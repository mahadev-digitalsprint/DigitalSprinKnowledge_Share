from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionDep
from app.config import settings
from app.core.registry import resolve_embedding_profile
from app.db import CollectionDB
from app.models.schemas import CollectionCreate, CollectionOut

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=list[CollectionOut])
async def list_collections(session: SessionDep) -> Sequence[CollectionDB]:
    result = await session.execute(
        select(CollectionDB).where(CollectionDB.org_id == settings.default_org_id)
    )
    return result.scalars().all()


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
    )
    session.add(coll)
    await session.commit()
    await session.refresh(coll)
    return coll


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: str, session: SessionDep) -> None:
    result = await session.execute(
        select(CollectionDB).where(CollectionDB.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    await session.delete(coll)
    await session.commit()
