"""Tests for state association and club CRUD + tenant scoping."""

from __future__ import annotations


def test_state_crud_and_scoping(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers

    # Create
    r = c.post("/api/v1/states", json={"name": "Lagos", "code": "LAG"}, headers=h)
    assert r.status_code == 201, r.text
    state = r.json()
    assert state["name"] == "Lagos"
    assert state["federation_id"] == admin_ctx.federation_id

    # List
    r = c.get("/api/v1/states", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # Search miss
    assert c.get("/api/v1/states?q=zzz", headers=h).json()["total"] == 0

    # Update
    r = c.put(f"/api/v1/states/{state['id']}", json={"code": "LG"}, headers=h)
    assert r.status_code == 200
    assert r.json()["code"] == "LG"

    # Delete (soft) then 404
    assert c.delete(f"/api/v1/states/{state['id']}", headers=h).status_code == 200
    assert c.get(f"/api/v1/states/{state['id']}", headers=h).status_code == 404


def test_states_require_auth(client):
    assert client.get("/api/v1/states").status_code == 401
    assert client.post("/api/v1/states", json={"name": "X"}).status_code == 401


def test_club_requires_valid_state(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    import uuid

    # state from another federation / nonexistent -> 422
    r = c.post(
        "/api/v1/clubs",
        json={"name": "Ghost Club", "state_id": str(uuid.uuid4())},
        headers=h,
    )
    assert r.status_code == 422, r.text


def test_club_crud(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers

    state = c.post("/api/v1/states", json={"name": "Oyo"}, headers=h).json()
    r = c.post(
        "/api/v1/clubs",
        json={"name": "Smash Club", "state_id": state["id"], "coach_name": "Coach A"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    club = r.json()

    detail = c.get(f"/api/v1/clubs/{club['id']}", headers=h).json()
    assert detail["state_name"] == "Oyo"
    assert detail["player_count"] == 0

    # duplicate name conflicts
    dup = c.post("/api/v1/clubs", json={"name": "Smash Club"}, headers=h)
    assert dup.status_code == 409
