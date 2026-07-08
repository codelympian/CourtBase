"""Tests for the storage service and image upload endpoints.

These run without a live Supabase: they cover validation and the behaviour when
object storage is not configured (the default in the test environment).
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from app.services import storage_service
from app.services.errors import ValidationError


def _upload(content_type: str, data: bytes):
    return SimpleNamespace(content_type=content_type, file=io.BytesIO(data))


def test_read_and_validate_accepts_png():
    content, ext = storage_service.read_and_validate(_upload("image/png", b"abc"))
    assert ext == "png"
    assert content == b"abc"


def test_read_and_validate_rejects_bad_type():
    with pytest.raises(ValidationError):
        storage_service.read_and_validate(_upload("text/plain", b"hello"))


def test_read_and_validate_rejects_empty():
    with pytest.raises(ValidationError):
        storage_service.read_and_validate(_upload("image/jpeg", b""))


def test_object_path_from_url():
    url = (
        "https://x.supabase.co/storage/v1/object/public/player-photos/"
        "fed-1/player-1.png?v=123"
    )
    assert storage_service.object_path_from_url("player-photos", url) == "fed-1/player-1.png"
    # Wrong bucket / missing / foreign URL -> None
    assert storage_service.object_path_from_url("club-logos", url) is None
    assert storage_service.object_path_from_url("player-photos", None) is None
    assert storage_service.object_path_from_url("player-photos", "https://other/x.png") is None


def test_photo_upload_without_storage_returns_503(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    created = c.post(
        "/api/v1/players",
        headers=h,
        json={"federation_player_code": "P1", "full_name": "Ada Lovelace", "gender": "F"},
    )
    assert created.status_code == 201, created.text
    player_id = created.json()["id"]

    # A valid image, but storage is not configured in tests -> 503.
    resp = c.post(
        f"/api/v1/players/{player_id}/photo",
        headers=h,
        files={"file": ("p.png", b"fakepngbytes", "image/png")},
    )
    assert resp.status_code == 503, resp.text

    # An unsupported type is rejected by validation first -> 422.
    bad = c.post(
        f"/api/v1/players/{player_id}/photo",
        headers=h,
        files={"file": ("p.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 422, bad.text
