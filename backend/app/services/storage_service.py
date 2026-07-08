"""Supabase Storage integration for images (player photos, club logos).

Talks to the Supabase Storage REST API with the service_role key. Buckets are
public-read (display on the public site); writes are authorized by our own RBAC.
"""

from __future__ import annotations

import time

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.services.errors import StorageError, ValidationError

# content-type -> file extension
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_TIMEOUT = httpx.Timeout(30.0)
# Buckets confirmed to exist this process (avoid re-creating on every upload).
_ensured_buckets: set[str] = set()


def _max_bytes() -> int:
    return settings.STORAGE_MAX_IMAGE_MB * 1024 * 1024


def _base_url() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1"


def _headers() -> dict[str, str]:
    key = settings.SUPABASE_SERVICE_KEY
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _require_enabled() -> None:
    if not settings.storage_enabled:
        raise StorageError(
            "Object storage is not configured (set SUPABASE_URL and SUPABASE_SERVICE_KEY)"
        )


def read_and_validate(file: UploadFile) -> tuple[bytes, str]:
    """Read an uploaded image, validating content-type and size.

    Returns ``(content_bytes, extension)``. Raises ``ValidationError`` on bad input.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_IMAGE_TYPES.get(content_type)
    if ext is None:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_TYPES)) or "none"
        raise ValidationError(f"Unsupported image type '{content_type}'. Allowed: {allowed}")
    content = file.file.read()
    if not content:
        raise ValidationError("Uploaded file is empty")
    if len(content) > _max_bytes():
        raise ValidationError(
            f"Image exceeds the {settings.STORAGE_MAX_IMAGE_MB} MB limit"
        )
    return content, ext


def public_url(bucket: str, path: str) -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"


def object_path_from_url(bucket: str, url: str | None) -> str | None:
    """Extract the storage object path from a stored public URL (ignores query)."""
    if not url:
        return None
    marker = f"/object/public/{bucket}/"
    idx = url.find(marker)
    if idx == -1:
        return None
    return url[idx + len(marker):].split("?", 1)[0]


def ensure_bucket(bucket: str) -> None:
    """Create the bucket (public) if it does not already exist. Idempotent."""
    _require_enabled()
    if bucket in _ensured_buckets:
        return
    payload = {
        "id": bucket,
        "name": bucket,
        "public": True,
        "file_size_limit": _max_bytes(),
        "allowed_mime_types": sorted(ALLOWED_IMAGE_TYPES),
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_base_url()}/bucket", headers=_headers(), json=payload)
    except httpx.HTTPError as exc:
        raise StorageError(f"Could not reach object storage: {exc}") from exc
    # 200 = created. An existing bucket returns 400/409 with a "already exists" message.
    if resp.status_code < 300 or "already exists" in resp.text.lower():
        _ensured_buckets.add(bucket)
        return
    raise StorageError(f"Failed to create bucket '{bucket}': {resp.status_code} {resp.text}")


def upload_image(bucket: str, path: str, content: bytes, ext: str) -> str:
    """Upload (upsert) an image and return its cache-busted public URL."""
    _require_enabled()
    ensure_bucket(bucket)
    content_type = next(ct for ct, e in ALLOWED_IMAGE_TYPES.items() if e == ext)
    headers = {
        **_headers(),
        "Content-Type": content_type,
        "x-upsert": "true",
        "cache-control": "3600",
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/object/{bucket}/{path}", headers=headers, content=content
            )
    except httpx.HTTPError as exc:
        raise StorageError(f"Could not reach object storage: {exc}") from exc
    if resp.status_code >= 300:
        raise StorageError(f"Upload failed: {resp.status_code} {resp.text}")
    # Cache-buster so overwritten images refresh in the browser/CDN.
    return f"{public_url(bucket, path)}?v={int(time.time())}"


def delete_object(bucket: str, path: str) -> None:
    """Best-effort delete; storage errors are swallowed (DB is source of truth)."""
    if not settings.storage_enabled or not path:
        return
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            client.delete(f"{_base_url()}/object/{bucket}/{path}", headers=_headers())
    except httpx.HTTPError:
        pass
