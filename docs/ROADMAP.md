# BFMS — Implementation Roadmap

Built in phases; each phase ends functional, tested, and deployable.

## ✅ Phase 1 — Foundation (current)
- [x] System architecture & multi-tenancy model ([ARCHITECTURE.md](ARCHITECTURE.md))
- [x] Normalized PostgreSQL schema + ERD ([DATABASE.md](DATABASE.md))
- [x] Monorepo folder structure (backend + frontend + docs)
- [x] API design ([API.md](API.md))
- [x] SQLAlchemy models for all 18 tables (multi-tenant, soft delete, timestamps, FKs, indexes)
- [x] Alembic migrations + dev database
- [x] Authentication: register, login, JWT access + refresh (rotating), logout, password reset, `/me`
- [x] RBAC (roles, permissions, route guards) + audit logging scaffold
- [x] Security: Argon2id hashing, CORS, rate limiting, input validation
- [x] Frontend scaffold: Next.js 15, Tailwind, shadcn/ui, TanStack Query, login + dashboard shell
- [x] Backend auth tests

## ✅ Phase 2 — Player / Club / State management (current)
- [x] CRUD APIs + UI for state associations, clubs, players (tenant-scoped, soft delete, audited)
- [x] CSV/Excel import & export for players (openpyxl; upsert by federation code)
- [x] Search, filtering (status/gender/club/state), pagination
- [x] Dashboard stat cards wired to a live `/stats/overview` endpoint
- [x] 20 backend tests passing, ruff clean; frontend build + typecheck pass
- [ ] Photo/logo upload to Supabase Storage (URL fields ready; upload deferred — needs Supabase keys)

## Phase 3 — Tournaments
- [ ] Tournament + event CRUD, status lifecycle
- [ ] Registration with age/membership/duplicate validation
- [ ] Draw generator (seeds, byes, random placement, knockout)
- [ ] Match score entry, automatic winner advancement & bracket updates

## Phase 4 — Ranking engine
- [ ] Configurable ranking rules & points tables
- [ ] Automatic point awards, recalculation, tie resolution
- [ ] Ranking history, movement, timeline, historical graphs
- [ ] Public rankings + admin approval/publish flow

## Phase 5 — Reports, public API, deployment
- [ ] Reports (PDF/Excel/CSV): player list, results, rankings, club & state rankings
- [ ] Public website API (rankings, players, tournaments, results)
- [ ] Notifications (email/SMS/push) module
- [ ] Deploy: Vercel (frontend), Render (backend), Supabase (DB + storage), CI/CD
