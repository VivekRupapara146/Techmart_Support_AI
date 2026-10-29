# TechMart Support — Frontend

React + TypeScript + Tailwind (Vite). Talks to the FastAPI backend's
`/v1/*` API — see [`../backend/README.md`](../backend/README.md) for the
endpoint contract and [`../README.md`](../README.md) for the architecture
overview.

## Run locally

**Prerequisites:** Node.js 20+

```bash
npm install
echo "VITE_API_BASE_URL=http://localhost:8000/v1" > .env.local
npm run dev
```
Requires the backend running at that URL (see `../backend/README.md`, or
`docker compose up` from the repo root). Opens at http://localhost:3000.

## Build for production

```bash
VITE_API_BASE_URL=https://your-backend-url/v1 npm run build
```
`VITE_API_BASE_URL` **must** be set at build time, not runtime — Vite
inlines it into the built JS. See [`../DEPLOYMENT.md`](../DEPLOYMENT.md)
for how each deployment target (Render static site, AWS, etc.) sets it.
Output goes to `dist/` — any static file host serves it.

## Type-check

```bash
npm run lint   # tsc --noEmit
```

## Notes on what's real vs. not yet wired up

This UI was originally scaffolded with a richer "enterprise console" demo
data layer (fabricated infra metrics, ticket/SLA workflows, invented
benchmark numbers) as an offline fallback for when no backend is reachable
— `src/services/apiClient.ts`'s catch blocks. Once the real backend
responds, those fallbacks are never used; a few panels (`OperationsView`,
`BenchmarksView`) still reference some of those cosmetic-only fields that
the real `/v1/health` and `/v1/evaluation/summary` endpoints intentionally
don't send (no fake Redis/replica-cluster stats) — a known follow-up is
trimming those specific fields from the UI rather than leaving them blank.
