# CourtBase — Badminton Federation Management System (BFMS)

A production-ready, **multi-tenant SaaS** platform for national badminton federations.
It replaces spreadsheets and manual processes with a centralized system for managing
players, clubs, tournaments, rankings, officials, and public information — and can serve
multiple federations (or other racket sports) from a single deployment.

> **Status:** Phase 1 complete — system architecture, normalized database schema,
> migrations, folder structure, API design, and JWT authentication with RBAC.

## Tech Stack

| Layer       | Technology |
|-------------|------------|
| Frontend    | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, React Hook Form, Zod, Recharts |
| Backend     | FastAPI, Python 3.13+, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth, RBAC |
| Database    | PostgreSQL (Supabase in production; local Postgres for dev) |
| Storage     | Supabase Storage (player photos, tournament docs, club logos, ranking exports) |
| Deployment  | Frontend → Vercel · Backend → Render · Database → Supabase |

## Monorepo Layout

```
BFMS/  (repo: CourtBase)
├── backend/      FastAPI application, SQLAlchemy models, Alembic migrations, tests
├── frontend/     Next.js 15 App Router application
├── docs/         Architecture, database/ERD, API spec, roadmap
└── README.md
```

## Quick Start

### Backend
```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # then edit DATABASE_URL + SECRET_KEY
alembic upgrade head            # run migrations
python -m app.seed              # optional: seed roles + super admin
uvicorn app.main:app --reload   # http://localhost:8000  (docs at /docs)
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local      # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                     # http://localhost:3000
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture & multi-tenancy model
- [docs/DATABASE.md](docs/DATABASE.md) — ERD and normalized schema
- [docs/API.md](docs/API.md) — REST API specification
- [docs/ROADMAP.md](docs/ROADMAP.md) — phased implementation plan

## Roles (RBAC)

`super_admin` · `federation_admin` · `tournament_official` · `club_admin` · `player` · `public`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full permission matrix.

## License

MIT
