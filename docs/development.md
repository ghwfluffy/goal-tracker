# Development Flow

This document captures the current implemented developer workflow for the Phase 0 foundation.

## Validation

Run the full repository validation flow from the repo root:

```bash
./scripts/validate.sh
```

That script runs:

1. backend linting via [`api/lint.sh`](/home/tfuller/git/goals/api/lint.sh)
2. backend tests via [`api/test.sh`](/home/tfuller/git/goals/api/test.sh)
3. frontend tests via [`web/test.sh`](/home/tfuller/git/goals/web/test.sh)
4. frontend production build via [`web/build.sh`](/home/tfuller/git/goals/web/build.sh)

## Smoke Test Contract

The initial end-to-end smoke path is:

1. the Vue landing page loads
2. the frontend requests `GET /api/v1/status`
3. the FastAPI backend returns application name, environment, status, version, and timestamp
4. the landing page renders the returned version

This is the baseline connectivity check that future feature work should preserve while auth, persistence, and goal flows are added.

## Local Run Commands

Backend:

```bash
cd api
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd web
npm install
npm run dev -- --host 0.0.0.0 --port 8081
```

The Vite dev server proxies `/api/*` requests to the backend by default.

## PostgreSQL 18 Note

The PostgreSQL service uses the PostgreSQL 18+ volume layout and mounts the named volume at `/var/lib/postgresql`.

If the local `postgres-data` volume was created from an earlier incorrect `/var/lib/postgresql/data` mount and you do not need to preserve that local data, recreate it with:

```bash
docker compose down -v
docker compose up --build
```
