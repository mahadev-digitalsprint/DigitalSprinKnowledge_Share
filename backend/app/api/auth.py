from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.config import settings
from app.core.auth import create_access_token, hash_password, verify_password
from app.db import UserDB
from app.models.schemas import AuthResponse, AuthUser, LoginRequest, SignupRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_payload(user: UserDB) -> AuthUser:
    collections = [item.strip() for item in user.allowed_collections.split(",") if item.strip()]
    if not collections:
        collections = ["*"]
    return AuthUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        allowed_collections=collections,
    )


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(body: SignupRequest, session: SessionDep) -> AuthResponse:
    email = body.email.strip().lower()
    exists = await session.execute(select(UserDB.id).where(UserDB.email == email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    first_user_result = await session.execute(select(func.count()).select_from(UserDB))
    is_first_user = (first_user_result.scalar_one() or 0) == 0
    role = "admin" if is_first_user else ("admin" if body.role == "admin" else "employee")

    user = UserDB(
        org_id=settings.default_org_id,
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role=role,
        allowed_collections="*",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    user_payload = _to_user_payload(user)
    token = create_access_token(user.id, user.role, user_payload.allowed_collections)
    return AuthResponse(access_token=token, user=user_payload)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: SessionDep) -> AuthResponse:
    email = body.email.strip().lower()
    result = await session.execute(select(UserDB).where(UserDB.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_payload = _to_user_payload(user)
    token = create_access_token(user.id, user.role, user_payload.allowed_collections)
    return AuthResponse(access_token=token, user=user_payload)
