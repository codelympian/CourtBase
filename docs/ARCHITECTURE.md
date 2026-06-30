# BFMS — System Architecture

## 1. Overview

BFMS (product name **CourtBase**) is a multi-tenant SaaS. A single deployment serves many
**federations**; each federation's data (players, clubs, tournaments, rankings, officials)
is logically isolated. Isolation is enforced at the application layer via a `federation_id`
foreign key on every tenant-scoped table plus query-scoping dependencies, and can be
hardened later with PostgreSQL Row-Level Security (RLS) on Supabase.

```
Platform
└── Federation (tenant)
    ├── Users / Officials
    ├── State Associations
    ├── Clubs
    ├── Players
    ├── Tournaments → Events → Registrations → Matches
    └── Ranking Rules → Ranking Points → Rankings → Ranking History
```

## 2. High-Level Diagram

```
┌──────────────┐    HTTPS/JSON     ┌─────────────────────┐     SQL      ┌──────────────┐
│  Next.js 15  │  ───────────────► │   FastAPI backend   │ ───────────► │ PostgreSQL   │
│  (Vercel)    │  ◄─────────────── │   (Render)          │ ◄─────────── │ (Supabase)   │
└──────────────┘   JWT in header   └─────────────────────┘              └──────────────┘
       │                                     │                                  ▲
       │                                     │  signed URLs                     │
       └───────── Supabase Storage ◄─────────┘   (photos, logos, exports) ──────┘
```

## 3. Backend Architecture (layered)

```
app/
├── main.py            App factory, middleware, router mounting, exception handlers
├── core/              Cross-cutting: config, database, security, RBAC, rate limiting, types
├── models/            SQLAlchemy ORM models (one concern per file)
├── schemas/           Pydantic request/response models (validation boundary)
├── api/v1/routes/     Thin HTTP controllers — parse, authorize, delegate
├── services/          Business logic (auth, audit, ranking engine, draws, ...)
└── utils/             Helpers (pagination, csv/excel, ...)
```

**Request flow:** `route → dependency (auth + RBAC + tenant scope) → service → model → DB`.
Routes stay thin; business rules live in services so they are unit-testable and reusable.

### Dependency injection chain (auth)
1. `get_db` — yields a scoped SQLAlchemy session.
2. `get_current_user` — decodes the JWT access token, loads the active user.
3. `get_current_active_user` — rejects disabled/soft-deleted users.
4. `require_roles(...)` / `require_permission(...)` — RBAC guard.
5. `get_tenant` — resolves and pins the caller's `federation_id` for query scoping.

## 4. Multi-Tenancy Model

- **Tenant key:** `federations.id`. Every tenant-scoped table carries a non-null
  `federation_id` FK with an index.
- **Platform-level (non-tenant) tables:** `federations`, `roles`, and the global
  `super_admin` users who administer the platform.
- **Scoping:** Non-super-admin requests are automatically filtered to the caller's
  `federation_id`. Cross-tenant access is impossible through the API.
- **Uniqueness:** Natural keys are unique *within* a federation, e.g.
  `UNIQUE (federation_id, federation_player_code)`, `UNIQUE (federation_id, email)` for players.
- **Future hardening:** enable Supabase RLS policies keyed on a `app.current_federation`
  session variable for defense-in-depth.

## 5. Authentication & Authorization

- **Passwords:** Argon2id hashing (`argon2-cffi`). No plaintext, ever.
- **Tokens:** short-lived **access JWT** (15 min) + long-lived **refresh JWT** (7 days).
  Refresh tokens are persisted (`refresh_tokens` table) so they can be revoked/rotated.
- **Token rotation:** each refresh issues a new refresh token and revokes the old one
  (reuse detection → revoke the whole family).
- **RBAC:** roles map to permissions; route guards check the user's role(s).

### Role → permission matrix (summary)

| Capability                         | super_admin | federation_admin | tournament_official | club_admin | player | public |
|------------------------------------|:-----------:|:----------------:|:-------------------:|:----------:|:------:|:------:|
| Manage users & system config       | ✅ | — | — | — | — | — |
| Configure ranking rules            | ✅ | — | — | — | — | — |
| Create tournaments, manage clubs   | ✅ | ✅ | — | — | — | — |
| Register/import players, export    | ✅ | ✅ | — | club only | — | — |
| Approve rankings                   | ✅ | ✅ | — | — | — | — |
| Manage draws, enter scores, finalize | ✅ | ✅ | ✅ | — | — | — |
| Update own club's players          | ✅ | ✅ | — | ✅ | — | — |
| View own profile/history           | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| View public rankings/results       | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 6. Security

- RBAC (above) + per-tenant query scoping.
- Input validation at the boundary via Pydantic v2 schemas.
- Rate limiting (SlowAPI) — stricter limits on auth endpoints.
- Argon2id password hashing.
- Audit logging of mutating actions (`audit_logs`).
- CORS allow-list driven by config.
- CSRF: the API is token-based (Authorization header, not cookies) which avoids classic
  CSRF; if cookie-based sessions are later added, double-submit CSRF tokens will be used.
- Secrets via environment variables only.

## 7. Conventions

- **Primary keys:** UUID (portable `GUID` type — native `uuid` on Postgres, `CHAR(36)`
  on SQLite for tests).
- **Soft deletes:** `deleted_at TIMESTAMPTZ NULL`; default queries exclude soft-deleted rows.
- **Timestamps:** `created_at` / `updated_at` (server defaults, auto-updated).
- **Enums:** typed `str`/`Enum` validated by Pydantic and constrained in the DB.
- **API versioning:** all endpoints under `/api/v1`.
- **Pagination:** `?page=&size=` with a standard `{items, total, page, size, pages}` envelope.
