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

## Phase 2 — Player / Club / State management
- [ ] CRUD APIs + UI for state associations, clubs, players
- [ ] CSV/Excel import & export for players
- [ ] Search, filtering, pagination
- [ ] Photo/logo upload to Supabase Storage

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
