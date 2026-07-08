"""Integration tests for the Phase 3 tournament lifecycle: categories, events,
registrations (with validation), draw generation, match scoring & advancement,
walkover, and tournament finalize."""

from __future__ import annotations

import uuid


def _make_player(c, h, code, name, gender="M", dob=None, status="active"):
    payload = {
        "federation_player_code": code,
        "full_name": name,
        "gender": gender,
        "status": status,
    }
    if dob:
        payload["date_of_birth"] = dob
    r = c.post("/api/v1/players", json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _make_category(c, h, code="OPEN", discipline="singles", gender_scope="any", **extra):
    payload = {"code": code, "name": code, "discipline": discipline, "gender_scope": gender_scope}
    payload.update(extra)
    r = c.post("/api/v1/event-categories", json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _make_tournament(c, h, name="Nationals", level="national_championship"):
    r = c.post("/api/v1/tournaments", json={"name": name, "level": level}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _make_event(c, h, tournament_id, category_id):
    r = c.post(
        f"/api/v1/tournaments/{tournament_id}/events",
        json={"category_id": category_id},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _open_registration(c, h, tournament_id):
    r = c.put(
        f"/api/v1/tournaments/{tournament_id}",
        json={"status": "registration_open"},
        headers=h,
    )
    assert r.status_code == 200, r.text


def _register(c, h, event_id, player_id, seed=None, partner_id=None, confirm=True):
    body = {"player_id": player_id}
    if seed is not None:
        body["seed"] = seed
    if partner_id is not None:
        body["partner_player_id"] = partner_id
    r = c.post(f"/api/v1/events/{event_id}/registrations", json=body, headers=h)
    assert r.status_code == 201, r.text
    reg = r.json()
    if confirm:
        r2 = c.put(
            f"/api/v1/registrations/{reg['id']}", json={"status": "confirmed"}, headers=h
        )
        assert r2.status_code == 200, r2.text
        reg = r2.json()
    return reg


def test_event_category_crud(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    cat = _make_category(c, h, code="MS", name="Men's Singles", gender_scope="men")
    assert cat["code"] == "MS"

    listed = c.get("/api/v1/event-categories", headers=h).json()
    assert any(x["id"] == cat["id"] for x in listed)

    upd = c.put(
        f"/api/v1/event-categories/{cat['id']}", json={"name": "Men's Singles A"}, headers=h
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Men's Singles A"

    assert c.delete(f"/api/v1/event-categories/{cat['id']}", headers=h).status_code == 200


def test_tournament_and_event_crud(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    cat = _make_category(c, h, code="WS", gender_scope="women")
    event = _make_event(c, h, t["id"], cat["id"])
    assert event["status"] == "pending"

    detail = c.get(f"/api/v1/tournaments/{t['id']}", headers=h).json()
    assert detail["event_count"] == 1

    # Duplicate category for the same tournament is rejected.
    dup = c.post(
        f"/api/v1/tournaments/{t['id']}/events", json={"category_id": cat["id"]}, headers=h
    )
    assert dup.status_code == 409


def test_registration_validations(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    junior = _make_category(c, h, code="U13", gender_scope="any", age_max=12)
    event = _make_event(c, h, t["id"], junior["id"])

    # Registration is rejected before the tournament opens registration.
    p_no_dob = _make_player(c, h, "R1", "No Dob")
    closed = c.post(
        f"/api/v1/events/{event['id']}/registrations",
        json={"player_id": p_no_dob["id"]},
        headers=h,
    )
    assert closed.status_code == 422

    _open_registration(c, h, t["id"])

    # Missing DOB on an age-restricted category -> rejected.
    r = c.post(
        f"/api/v1/events/{event['id']}/registrations",
        json={"player_id": p_no_dob["id"]},
        headers=h,
    )
    assert r.status_code == 422

    # Too old for U13.
    p_old = _make_player(c, h, "R2", "Too Old", dob="2005-01-01")
    r = c.post(
        f"/api/v1/events/{event['id']}/registrations", json={"player_id": p_old["id"]}, headers=h
    )
    assert r.status_code == 422

    # Eligible junior player registers fine.
    p_ok = _make_player(c, h, "R3", "Just Right", dob="2015-01-01")
    ok = c.post(
        f"/api/v1/events/{event['id']}/registrations", json={"player_id": p_ok["id"]}, headers=h
    )
    assert ok.status_code == 201, ok.text

    # Duplicate registration for the same player -> conflict.
    dup = c.post(
        f"/api/v1/events/{event['id']}/registrations", json={"player_id": p_ok["id"]}, headers=h
    )
    assert dup.status_code == 409

    # Inactive player cannot register (membership check).
    p_inactive = _make_player(c, h, "R4", "Inactive One", dob="2015-01-01", status="suspended")
    r = c.post(
        f"/api/v1/events/{event['id']}/registrations",
        json={"player_id": p_inactive["id"]},
        headers=h,
    )
    assert r.status_code == 422


def test_gender_scope_and_mixed_doubles(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    _open_registration(c, h, t["id"])

    mens = _make_category(c, h, code="MS2", gender_scope="men")
    event = _make_event(c, h, t["id"], mens["id"])
    woman = _make_player(c, h, "G1", "Wanda Woman", gender="F")
    r = c.post(
        f"/api/v1/events/{event['id']}/registrations", json={"player_id": woman["id"]}, headers=h
    )
    assert r.status_code == 422

    mixed = _make_category(c, h, code="XD2", discipline="doubles", gender_scope="mixed")
    xevent = _make_event(c, h, t["id"], mixed["id"])
    man = _make_player(c, h, "G2", "Mike Man", gender="M")
    woman2 = _make_player(c, h, "G3", "Wendy Woman", gender="F")
    man2 = _make_player(c, h, "G4", "Mo Man", gender="M")

    # Doubles requires a partner.
    no_partner = c.post(
        f"/api/v1/events/{xevent['id']}/registrations", json={"player_id": man["id"]}, headers=h
    )
    assert no_partner.status_code == 422

    # Same-gender pair rejected for mixed doubles.
    same_gender = c.post(
        f"/api/v1/events/{xevent['id']}/registrations",
        json={"player_id": man["id"], "partner_player_id": man2["id"]},
        headers=h,
    )
    assert same_gender.status_code == 422

    # Valid mixed pair accepted.
    ok = c.post(
        f"/api/v1/events/{xevent['id']}/registrations",
        json={"player_id": man["id"], "partner_player_id": woman2["id"]},
        headers=h,
    )
    assert ok.status_code == 201, ok.text


def test_draw_generation_seeds_and_byes(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    _open_registration(c, h, t["id"])
    cat = _make_category(c, h, code="OPEN5")
    event = _make_event(c, h, t["id"], cat["id"])

    players = [_make_player(c, h, f"D{i}", f"Player {i}") for i in range(5)]
    _register(c, h, event["id"], players[0]["id"], seed=1)
    _register(c, h, event["id"], players[1]["id"], seed=2)
    for p in players[2:]:
        _register(c, h, event["id"], p["id"])

    # Not enough confirmed players -> can't generate below 2 (sanity: already have 5, skip).
    draw = c.post(f"/api/v1/events/{event['id']}/draw", headers=h)
    assert draw.status_code == 200, draw.text
    matches = draw.json()
    # draw_size for 5 players -> 8 slots: 4 R1 + 2 R2 + 1 final = 7 matches.
    assert len(matches) == 7
    round1 = [m for m in matches if m["round"] == 1]
    assert len(round1) == 4
    byes = [m for m in round1 if m["status"] == "bye"]
    assert len(byes) == 3  # 8 - 5 = 3 byes
    for b in byes:
        assert b["winner_id"] is not None

    # Seed 1 and seed 2 must be on opposite halves (slots 0..3 vs 4..7), i.e.
    # they cannot appear in the same round-1 match.
    seed1_match = next(m for m in round1 if players[0]["id"] in (m["player1_id"], m["player2_id"]))
    assert players[1]["id"] not in (seed1_match["player1_id"], seed1_match["player2_id"])

    event_after = c.get(f"/api/v1/events/{event['id']}", headers=h).json()
    assert event_after["status"] == "draw_published"

    # Cannot regenerate an existing draw.
    again = c.post(f"/api/v1/events/{event['id']}/draw", headers=h)
    assert again.status_code == 422

    # Cannot reset once... actually nothing played yet, reset should succeed.
    reset = c.delete(f"/api/v1/events/{event['id']}/draw", headers=h)
    assert reset.status_code == 200
    event_reset = c.get(f"/api/v1/events/{event['id']}", headers=h).json()
    assert event_reset["status"] == "pending"
    assert event_reset["draw_size"] is None


def test_match_scoring_advancement_and_finalize(admin_ctx):
    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    _open_registration(c, h, t["id"])
    cat = _make_category(c, h, code="OPEN4")
    event = _make_event(c, h, t["id"], cat["id"])

    players = [_make_player(c, h, f"M{i}", f"Match Player {i}") for i in range(4)]
    for p in players:
        _register(c, h, event["id"], p["id"])

    draw = c.post(f"/api/v1/events/{event['id']}/draw", headers=h)
    assert draw.status_code == 200, draw.text
    matches = draw.json()
    assert len(matches) == 3  # 2 R1 + 1 final, no byes (4 is already a power of 2)
    round1 = sorted((m for m in matches if m["round"] == 1), key=lambda m: m["position"])
    final = next(m for m in matches if m["round"] == 2)

    # Invalid score: tie.
    bad = c.post(
        f"/api/v1/matches/{round1[0]['id']}/score", json={"score": [[21, 21]]}, headers=h
    )
    assert bad.status_code == 422

    # Record valid straight-games win for round1[0].
    r1 = c.post(
        f"/api/v1/matches/{round1[0]['id']}/score",
        json={"score": [[21, 15], [21, 18]]},
        headers=h,
    )
    assert r1.status_code == 200, r1.text
    winner1 = r1.json()["winner_id"]
    assert winner1 in (round1[0]["player1_id"], round1[0]["player2_id"])

    # Event should now be "ongoing" (draw_published -> ongoing on first score).
    event_mid = c.get(f"/api/v1/events/{event['id']}", headers=h).json()
    assert event_mid["status"] == "ongoing"

    # Winner should have advanced into the final's slot.
    final_after = c.get(f"/api/v1/matches/{final['id']}", headers=h).json()
    assert winner1 in (final_after["player1_id"], final_after["player2_id"])

    # Cannot score the same match twice.
    again = c.post(
        f"/api/v1/matches/{round1[0]['id']}/score",
        json={"score": [[21, 10], [21, 10]]},
        headers=h,
    )
    assert again.status_code == 422

    # Finalize is blocked while matches remain (round1[1] and the final).
    blocked = c.post(f"/api/v1/tournaments/{t['id']}/finalize", headers=h)
    assert blocked.status_code == 422

    # Walkover for round1[1].
    r2 = c.post(
        f"/api/v1/matches/{round1[1]['id']}/score",
        json={"walkover_winner_id": round1[1]["player1_id"]},
        headers=h,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "walkover"
    winner2 = r2.json()["winner_id"]

    # Play the final (best-of-3 with a decider).
    final_score = c.post(
        f"/api/v1/matches/{final['id']}/score",
        json={"score": [[21, 18], [18, 21], [21, 16]]},
        headers=h,
    )
    assert final_score.status_code == 200, final_score.text
    assert final_score.json()["winner_id"] in (winner1, winner2)

    event_done = c.get(f"/api/v1/events/{event['id']}", headers=h).json()
    assert event_done["status"] == "completed"

    finalize = c.post(f"/api/v1/tournaments/{t['id']}/finalize", headers=h)
    assert finalize.status_code == 200, finalize.text
    assert finalize.json()["status"] == "completed"


def test_tournament_official_can_score_but_not_manage_tournaments(admin_ctx):
    from types import SimpleNamespace

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.enums import RoleName
    from app.models.role import Role
    from app.models.user import User

    c, h = admin_ctx.client, admin_ctx.headers
    t = _make_tournament(c, h)
    _open_registration(c, h, t["id"])
    cat = _make_category(c, h, code="OPEN2")
    event = _make_event(c, h, t["id"], cat["id"])
    p1 = _make_player(c, h, "O1", "Official Test 1")
    p2 = _make_player(c, h, "O2", "Official Test 2")
    _register(c, h, event["id"], p1["id"])
    _register(c, h, event["id"], p2["id"])
    c.post(f"/api/v1/events/{event['id']}/draw", headers=h)
    match = c.get(f"/api/v1/events/{event['id']}/draw", headers=h).json()[0]

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == RoleName.tournament_official.value).first()
        email = f"official_{uuid.uuid4().hex[:8]}@example.com"
        password = "Official1!"
        user = User(
            federation_id=uuid.UUID(admin_ctx.federation_id),
            email=email,
            hashed_password=hash_password(password),
            full_name="Test Official",
            is_active=True,
            roles=[role],
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    login = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    official = SimpleNamespace(
        headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )

    # Official CAN enter a score.
    scored = c.post(
        f"/api/v1/matches/{match['id']}/score",
        json={"score": [[21, 10], [21, 10]]},
        headers=official.headers,
    )
    assert scored.status_code == 200, scored.text

    # Official CANNOT create a tournament (lacks tournaments:manage).
    forbidden = c.post(
        "/api/v1/tournaments",
        json={"name": "Not Allowed", "level": "open"},
        headers=official.headers,
    )
    assert forbidden.status_code == 403
