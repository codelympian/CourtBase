"""End-to-end tests for the authentication flow."""

from __future__ import annotations

import uuid


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


def register(client, email=None, password="Sup3rSecret!", full_name="Test User"):
    email = email or _unique_email()
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return email, password, resp


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_login(client):
    email, password, reg = register(client)
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["email"] == email
    assert "id" in body
    assert "hashed_password" not in body  # never leak the hash

    r = login(client, email, password)
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["expires_in"] > 0


def test_duplicate_registration_conflicts(client):
    email, password, _ = register(client)
    _, _, dup = register(client, email=email, password=password)
    assert dup.status_code == 409


def test_login_wrong_password(client):
    email, _, _ = register(client)
    r = login(client, email, "WrongPassword!")
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(client):
    email, password, _ = register(client)
    tokens = login(client, email, password).json()
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["email"] == email
    assert "permissions" in me and "roles" in me


def test_refresh_rotates_token(client):
    email, password, _ = register(client)
    tokens = login(client, email, password).json()
    old_refresh = tokens["refresh_token"]

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new_tokens = r.json()
    assert new_tokens["refresh_token"] != old_refresh

    # Reusing the old (now revoked) refresh token must fail.
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


def test_logout_revokes_refresh(client):
    email, password, _ = register(client)
    tokens = login(client, email, password).json()
    refresh = tokens["refresh_token"]

    assert client.post("/api/v1/auth/logout", json={"refresh_token": refresh}).status_code == 200
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401


def test_password_reset_flow(client):
    email, password, _ = register(client)
    forgot = client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert forgot.status_code == 200
    detail = forgot.json()["detail"]
    # Dev mode returns the token inline.
    assert "dev only" in detail
    token = detail.split(":", 1)[1].strip()

    new_password = "BrandNewPass1!"
    reset = client.post(
        "/api/v1/auth/password/reset", json={"token": token, "new_password": new_password}
    )
    assert reset.status_code == 200

    assert login(client, email, password).status_code == 401  # old password invalid
    assert login(client, email, new_password).status_code == 200


def test_invalid_token_rejected(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
