# BFMS — REST API Specification

Base URL: `/api/v1`. JSON in/out. Auth via `Authorization: Bearer <access_token>`.
All list endpoints accept `?page=&size=&q=&sort=` and return a paginated envelope.

## Conventions

- **Auth header:** `Authorization: Bearer <jwt>`.
- **Errors:** `{ "detail": "message" }` (or a list of field errors for 422), with proper HTTP status.
- **Pagination envelope:** `{ "items": [...], "total": n, "page": p, "size": s, "pages": k }`.
- **Tenancy:** non-super-admin callers are implicitly scoped to their federation.

## Phase 1 — Authentication (implemented)

| Method | Path                       | Auth        | Description |
|--------|----------------------------|-------------|-------------|
| POST   | `/auth/register`           | public*     | Register a user (first user of a federation, or by invite). |
| POST   | `/auth/login`              | public      | Login with email + password → access + refresh tokens. |
| POST   | `/auth/refresh`            | refresh tkn | Rotate refresh token, issue new access token. |
| POST   | `/auth/logout`             | bearer      | Revoke the current refresh token. |
| POST   | `/auth/password/forgot`    | public      | Request a password-reset token (stubbed to notifications). |
| POST   | `/auth/password/reset`     | reset tkn   | Set a new password using a reset token. |
| GET    | `/auth/me`                 | bearer      | Current user profile + roles + federation. |
| GET    | `/health`                  | public      | Liveness/readiness probe. |

\* `register` is open for bootstrapping; in production it is gated behind invite/role.

### Examples

`POST /auth/login`
```json
// request
{ "email": "admin@federation.org", "password": "••••••••" }
// 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "expires_in": 900 }
```

`GET /auth/me` → `200`
```json
{
  "id": "uuid", "email": "admin@federation.org", "full_name": "Admin",
  "is_active": true, "federation_id": "uuid",
  "roles": ["federation_admin"]
}
```

## Phase 2 — Org & people (implemented)

All list endpoints support `?page=&size=` and return the pagination envelope; writes are
tenant-scoped and audited.

| Method | Path | Query / body | Roles |
|--------|------|--------------|-------|
| GET | `/states` | `q, page, size` | any authenticated |
| POST | `/states` | StateCreate | `states:manage` (federation_admin) |
| GET/PUT/DELETE | `/states/{id}` | — / StateUpdate / — | read: any · write: `states:manage` |
| GET | `/clubs` | `q, state_id, page, size` | any authenticated |
| POST | `/clubs` | ClubCreate | `clubs:manage` |
| GET/PUT/DELETE | `/clubs/{id}` | — / ClubUpdate / — | read: any · write: `clubs:manage` |
| GET | `/players` | `q, status, gender, club_id, state_id, page, size` | any authenticated |
| POST | `/players` | PlayerCreate | `players:manage` |
| GET/PUT/DELETE | `/players/{id}` | — / PlayerUpdate / — | read: any · write: `players:manage` |
| POST | `/players/import` | multipart `file` (CSV/XLSX), `?federation_id` (super admin) | `players:import` |
| GET | `/players/export` | `format=csv\|xlsx` | `reports:export` |
| POST/DELETE | `/players/{id}/photo` | multipart `file` (PNG/JPEG/WebP ≤5MB) / — | `players:manage` |
| POST/DELETE | `/clubs/{id}/logo` | multipart `file` (PNG/JPEG/WebP ≤5MB) / — | `clubs:manage` |
| GET | `/stats/overview` | — | any authenticated |

Image uploads go to public Supabase Storage buckets (`player-photos`, `club-logos`),
auto-created on first use; the object's public URL (cache-busted) is stored on the row.
Returns 503 if storage isn't configured.

Players carry derived, unstored `age` and `age_category` (U11…U19 / Senior) in responses.
Import upserts by `(federation_id, federation_player_code)`; club/state are matched by name
within the federation. Returns `{created, updated, skipped, errors[]}`.

## Phase 3 — Tournaments (implemented)

| Method | Path | Roles |
|--------|------|-------|
| GET/POST | `/event-categories` | view: any auth · write: `tournaments:manage` |
| GET/PUT/DELETE | `/event-categories/{id}` | `tournaments:manage` (global cats: super admin only) |
| GET/POST | `/tournaments` | view: any auth · write: `tournaments:manage` |
| GET/PUT/DELETE | `/tournaments/{id}` | read: any · write: `tournaments:manage` |
| POST | `/tournaments/{id}/finalize` | `tournaments:finalize` |
| GET/POST | `/tournaments/{id}/events` | view: any auth · write: `tournaments:manage` |
| GET/PUT/DELETE | `/events/{id}` | read: any · write: `tournaments:manage` |
| GET/POST | `/events/{id}/registrations` | view: any auth · write: `tournaments:manage` |
| GET/PUT/DELETE | `/registrations/{id}` | read: any · write: `tournaments:manage` |
| POST/GET/DELETE | `/events/{id}/draw` | generate/reset: `draws:manage` · read: any auth |
| GET | `/matches/{id}` | any authenticated |
| POST | `/matches/{id}/score` | `scores:enter` |

Registration validates age eligibility, active membership, duplicate registration,
category gender scope, and (mixed doubles) opposite-gender partners — and only while the
tournament is `registration_open`. The draw generator seeds players into a standard
single-elimination bracket, awards byes when the field isn't a power of two, and
auto-advances winners. `/matches/{id}/score` accepts either `score` (best-of-3 game list,
BWF rules) or `walkover_winner_id`, updates the bracket, and marks the event
`ongoing`/`completed`. Finalize refuses while any match is unplayed.

## Phase 4 — Ranking engine (planned)

`/ranking-rules`, `/rankings` (current), `/rankings/recalculate`,
`/players/{id}/ranking-history`.

## Phase 5 — Public website API (planned, unauthenticated, cached)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/public/rankings` | Live published rankings (filter by category/state). |
| GET | `/public/players` | Public player directory. |
| GET | `/public/players/{id}` | Public player profile + stats. |
| GET | `/public/tournaments` | Tournaments (incl. upcoming). |
| GET | `/public/results` | Completed tournament results. |

Public endpoints require a federation selector (`?federation=<slug>`) and are read-only.
