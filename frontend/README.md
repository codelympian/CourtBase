# CourtBase — Frontend

Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn-style UI + TanStack Query.

## Setup
```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

## Scripts
- `npm run dev` — start the dev server
- `npm run build` — production build
- `npm run typecheck` — TypeScript check
- `npm run lint` — ESLint

## Structure
```
src/
├── app/                 App Router routes
│   ├── login/           Auth pages
│   └── dashboard/       Protected federation workspace (sidebar shell + modules)
├── components/
│   ├── ui/              shadcn-style primitives (button, input, card, label)
│   └── dashboard/       Sidebar, module placeholders
├── hooks/               TanStack Query auth hooks
├── lib/                 API client (JWT + auto-refresh), utils
└── providers/           Query provider
```

Auth uses the backend JWT access/refresh flow; tokens are stored client-side and the
API client transparently refreshes on `401`.
