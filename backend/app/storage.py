from __future__ import annotations

from pathlib import Path

from app.config import settings


def local_storage_root() -> Path:
    return Path(settings.local_storage_path).resolve()


def ensure_storage_ready() -> Path:
    root = local_storage_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_upload(content: bytes, object_key: str, content_type: str) -> None:
    destination = local_storage_root() / object_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
