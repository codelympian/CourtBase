# BFMS — Database Schema (ERD)

Fully normalized PostgreSQL schema. Every tenant-scoped table has `federation_id`,
soft deletes (`deleted_at`), and `created_at` / `updated_at`. UUID primary keys throughout.

## Entity-Relationship Diagram

```
                         ┌──────────────┐
                         │  federations │  (tenant root — platform level)
                         └──────┬───────┘
        ┌───────────────┬───────┼─────────────┬──────────────┬───────────────┐
        ▼               ▼       ▼             ▼              ▼               ▼
 ┌────────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
 │   users    │  │  states  │ │  clubs   │ │ players  │ │tournaments │ │ranking_rules│
 └─────┬──────┘  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘ └─────┬──────┘
       │ M:N (user_roles)          │            │             │              │
       ▼              states 1:N clubs 1:N players            │ 1:N          │ 1:N
 ┌──────────┐                                   │             ▼              ▼
 │  roles   │ (platform-level)        players───┘       ┌──────────┐  ┌──────────────┐
 └──────────┘                                           │  events  │  │ranking_points│
       ▲                                                └────┬─────┘  └──────────────┘
       │ refresh_tokens 1:N users                            │ 1:N
 ┌───────────────┐                                           ▼
 │ refresh_tokens│                                    ┌───────────────┐
 └───────────────┘                                    │ registrations │
                                                       └──────┬────────┘
 players 1:N ─┐                                               │
 ┌──────────┐ │  ┌──────────┐   events 1:N matches            │
 │ rankings │ │  │ matches  │◄────────────────────────────────┘
 └──────────┘ │  └──────────┘   (player1/player2 → players; winner → players)
 ┌────────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────┐
 │ ranking_history│  │ notifications│  │  audit_logs   │  │player_stats│
 └────────────────┘  └──────────────┘  └───────────────┘  └────────────┘
```

## Tables

### Platform-level
- **federations** — `id, name, slug (unique), country, contact_email, logo_url, primary_color, settings (JSON), is_active, timestamps, deleted_at`
- **roles** — `id, name (unique: super_admin|federation_admin|tournament_official|club_admin|player|public), description, permissions (JSON)`

### Identity & access (tenant-scoped, except platform super admins)
- **users** — `id, federation_id (nullable for platform super_admin), email, hashed_password, full_name, is_active, is_superuser, last_login_at, player_id (nullable 1:1 to players), timestamps, deleted_at`. `UNIQUE(federation_id, email)`.
- **user_roles** — `user_id, role_id` (composite PK; M:N).
- **refresh_tokens** — `id, user_id, token_hash (unique), family_id, expires_at, revoked_at, user_agent, ip, created_at`.

### Org structure
- **state_associations** — `id, federation_id, name, code, contact_email, contact_phone, timestamps, deleted_at`. `UNIQUE(federation_id, name)`.
- **clubs** — `id, federation_id, state_id (FK), name, coach_name, contact_email, contact_phone, address, logo_url, timestamps, deleted_at`. `UNIQUE(federation_id, name)`.
- **players** — `id, federation_id, federation_player_code, full_name, gender (M|F|O), date_of_birth, club_id (FK, nullable), state_id (FK, nullable), nationality, photo_url, phone, email, status (active|inactive|suspended|retired), timestamps, deleted_at`. `UNIQUE(federation_id, federation_player_code)`. Age category is **derived** from `date_of_birth` (not stored) to stay normalized.

### Tournaments & competition
- **tournaments** — `id, federation_id, name, venue, start_date, end_date, level (national_championship|open|invitational|ranking), status (draft|registration_open|registration_closed|ongoing|completed), organizer, ranking_rule_id (FK, nullable), timestamps, deleted_at`.
- **event_categories** — `id, federation_id (nullable=global default), code (e.g. MS, WS, MD, WD, XD, U11..U19), name, discipline (singles|doubles), gender_scope (men|women|mixed|any), age_min, age_max, is_active`. Extensible.
- **events** — `id, federation_id, tournament_id (FK), category_id (FK), name, draw_size, status, timestamps, deleted_at`. `UNIQUE(tournament_id, category_id)`.
- **registrations** — `id, federation_id, event_id (FK), player_id (FK), partner_player_id (FK, nullable for doubles), seed (nullable), status (pending|confirmed|withdrawn|rejected), created_at, deleted_at`. `UNIQUE(event_id, player_id)`; validated for age eligibility, membership, duplicates.
- **matches** — `id, federation_id, event_id (FK), round (int), position (int), player1_id, player2_id, winner_id, score (JSON list of game scores e.g. [[21,18],[18,21],[21,16]]), status (scheduled|in_progress|completed|walkover|bye), scheduled_at, next_match_id (FK self, for bracket advancement), timestamps, deleted_at`.

### Ranking engine
- **ranking_rules** — `id, federation_id, name, level (matches tournament level), category_id (nullable), config (JSON), is_active, timestamps, deleted_at`.
- **ranking_points** — `id, federation_id, rule_id (FK), result_key (winner|runner_up|semi_final|quarter_final|round_16|...), points (int)`. `UNIQUE(rule_id, result_key)`.
- **rankings** — `id, federation_id, player_id (FK), category_id (FK), points (int), rank (int), previous_rank (int, nullable), as_of (date), is_published, timestamps`. `UNIQUE(federation_id, player_id, category_id, as_of)`. Imported baseline rows are flagged via `source=import|computed`.
- **ranking_history** — `id, federation_id, player_id, category_id, rank, previous_rank, points, movement (int), reason, snapshot_date, created_at`. Append-only.

### Player statistics (denormalized read-model, recomputed from matches)
- **player_stats** — `id, federation_id, player_id, category_id (nullable=overall), matches_played, wins, losses, titles, finals, semi_finals, win_percentage, updated_at`.

### Platform services
- **notifications** — `id, federation_id, user_id (nullable), channel (email|sms|push), template, payload (JSON), status (queued|sent|failed), sent_at, created_at`.
- **audit_logs** — `id, federation_id (nullable), actor_user_id (nullable), action, entity_type, entity_id, before (JSON), after (JSON), ip, user_agent, created_at`.

## Indexes (beyond PKs/uniques)
- `federation_id` on every tenant table.
- `players(federation_id, status)`, `players(club_id)`, `players(state_id)`.
- `rankings(federation_id, category_id, rank)`, `ranking_history(player_id, snapshot_date)`.
- `matches(event_id, round, position)`, `registrations(event_id)`.
- `audit_logs(federation_id, created_at)`, `refresh_tokens(user_id)`, `refresh_tokens(family_id)`.

## Constraints & integrity
- FKs everywhere with sensible `ON DELETE` (RESTRICT for org structure, SET NULL for optional links).
- CHECK constraints on enums and on score/points ranges (e.g. `points >= 0`).
- Partial-unique semantics for soft deletes handled at the application layer (queries
  filter `deleted_at IS NULL`); natural-key uniqueness applies to live rows.
