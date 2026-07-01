"""Tests for player CRUD, filtering, and CSV import/export."""

from __future__ import annotations

import io


def _make_player(c, h, code="P001", name="Alice Smith", gender="F", **extra):
    payload = {"federation_player_code": code, "full_name": name, "gender": gender}
    payload.update(extra)
    return c.post("/api/v1/players", json=payload, headers=h)


def test_player_crud_and_derived_age(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    r = _make_player(c, h, date_of_birth="2012-01-01")
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["age_category"] in {"U15", "U13", "U17"}  # depends on run date
    assert p["age"] is not None

    # Get detail
    got = c.get(f"/api/v1/players/{p['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["full_name"] == "Alice Smith"

    # Update status
    r = c.put(f"/api/v1/players/{p['id']}", json={"status": "retired"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "retired"

    # Delete
    assert c.delete(f"/api/v1/players/{p['id']}", headers=h).status_code == 200
    assert c.get(f"/api/v1/players/{p['id']}", headers=h).status_code == 404


def test_player_duplicate_code_conflicts(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    assert _make_player(c, h, code="DUP1").status_code == 201
    assert _make_player(c, h, code="DUP1", name="Other").status_code == 409


def test_player_filters(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    _make_player(c, h, code="M1", name="Bob Male", gender="M")
    _make_player(c, h, code="F1", name="Carol Female", gender="F")

    males = c.get("/api/v1/players?gender=M", headers=h).json()
    assert all(item["gender"] == "M" for item in males["items"])
    assert males["total"] >= 1

    search = c.get("/api/v1/players?q=Carol", headers=h).json()
    assert any("Carol" in i["full_name"] for i in search["items"])


def test_player_csv_export_and_import(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    _make_player(c, h, code="EXP1", name="Export One", gender="M")

    # Export CSV
    r = c.get("/api/v1/players/export?format=csv", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "EXP1" in r.text

    # Import a new player via CSV upload
    csv_bytes = (
        b"federation_player_code,full_name,gender,date_of_birth,status,club_name,state_name\n"
        b"IMP1,Imported Player,F,2000-05-05,active,,\n"
        b"IMP1,Imported Player Updated,F,2000-05-05,active,,\n"  # same code -> update
        b",Missing Code,M,,active,,\n"  # invalid -> skipped
    )
    files = {"file": ("players.csv", io.BytesIO(csv_bytes), "text/csv")}
    r = c.post("/api/v1/players/import", files=files, headers=h)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["skipped"] == 1
    assert len(result["errors"]) == 1

    # The imported player should now be searchable with the updated name
    found = c.get("/api/v1/players?q=Imported", headers=h).json()
    assert any(i["full_name"] == "Imported Player Updated" for i in found["items"])


def test_player_write_requires_permission(client):
    # An unauthenticated user cannot create players.
    assert client.post("/api/v1/players", json={}).status_code == 401


def test_stats_overview(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    _make_player(c, h, code="S1", name="Stat One", gender="M")
    r = c.get("/api/v1/stats/overview", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_players"] >= 1
    assert "active_tournaments" in body
