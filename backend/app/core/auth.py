from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.config import settings


def _b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode())


def hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt_value}:{password}".encode()).hexdigest()
    return f"{salt_value}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: str, role: str, collections: list[str]) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.auth_token_ttl_hours)
    payload = {
        "sub": user_id,
        "role": role,
        "collections": collections,
        "exp": int(exp.timestamp()),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    payload_b64 = _b64_encode(payload_raw)
    sig = hmac.new(settings.auth_secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64_encode(sig)}"


def parse_access_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    expected_sig = hmac.new(
        settings.auth_secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    given_sig = _b64_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, given_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    payload = json.loads(_b64_decode(payload_b64).decode())
    exp = int(payload.get("exp", 0))
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload
