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

## Phase 2 — Org & people (planned)

| Method | Path | Roles |
|--------|------|-------|
| GET/POST | `/states` | view: any auth · write: federation_admin |
| GET/PUT/DELETE | `/states/{id}` | federation_admin |
| GET/POST | `/clubs` | view: any auth · write: federation_admin |
| GET/PUT/DELETE | `/clubs/{id}` | federation_admin / club_admin (own) |
| GET/POST | `/players` | view: any auth · write: federation_admin / club_admin (own club) |
| GET/PUT/DELETE | `/players/{id}` | federation_admin / club_admin (own) |
| POST | `/players/import` | federation_admin (CSV/Excel) |
| GET | `/players/export` | federation_admin (CSV/Excel) |

## Phase 3 — Tournaments (planned)

`/tournaments`, `/tournaments/{id}/events`, `/events/{id}/registrations`,
`/events/{id}/draw` (generate), `/matches/{id}/score`, `/tournaments/{id}/finalize`.

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
