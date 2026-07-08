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
- [x] Photo/logo upload to Supabase Storage (upload/delete endpoints + ImageUpload UI; set
      `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` to enable — public buckets auto-created)

## ✅ Phase 3 — Tournaments (current)
- [x] Tournament + event CRUD, status lifecycle (draft → registration → ongoing → completed)
- [x] Event categories (global Senior/Junior defaults + federation-custom); seeded MS/WS/MD/WD/XD/U11–U19
- [x] Registration with age eligibility, membership, duplicate, gender-scope & mixed-doubles validation
- [x] Draw generator (standard seeding, byes for non-power-of-two fields, random placement, knockout)
- [x] Match score entry (BWF rules, best-of-3), walkovers, automatic winner advancement & bracket updates
- [x] Tournament finalize (guards against unfinished matches)
- [x] 47 backend tests passing, ruff clean; frontend build/typecheck/lint pass; verified live on Supabase

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
