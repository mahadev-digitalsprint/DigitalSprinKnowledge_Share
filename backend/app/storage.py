from __future__ import annotations

from pathlib import Path

from minio import Minio

from app.config import settings


def uses_local_storage() -> bool:
    return settings.storage_provider.lower() == "local"


def local_storage_root() -> Path:
    return Path(settings.local_storage_path).resolve()


def ensure_storage_ready() -> Minio | None:
    if uses_local_storage():
        local_storage_root().mkdir(parents=True, exist_ok=True)
        return None

    minio = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )
    if not minio.bucket_exists(settings.minio_bucket):
        minio.make_bucket(settings.minio_bucket)
    return minio


def store_upload(content: bytes, object_key: str, content_type: str) -> None:
    if uses_local_storage():
        destination = local_storage_root() / object_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return

    from io import BytesIO

    minio = ensure_storage_ready()
    assert minio is not None
    minio.put_object(
        settings.minio_bucket,
        object_key,
        BytesIO(content),
        len(content),
        content_type=content_type or "application/octet-stream",
    )
