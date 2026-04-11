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

## Auth Foundation

Phase 0 now includes backend auth/session foundation endpoints:

1. `GET /api/v1/auth/bootstrap-status`
2. `POST /api/v1/auth/bootstrap`
3. `POST /api/v1/auth/login`
4. `GET /api/v1/auth/me`
5. `POST /api/v1/auth/logout`

The first account bootstrap path creates the initial administrator and starts a server-side session using an HTTP-only cookie.

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

If `web/node_modules` was created by Docker and is root-owned, the frontend test/build scripts will reuse the existing dependency tree instead of trying to reinstall into that directory. If dependency versions actually change, rebuild that directory from a writable environment.

## PostgreSQL 18 Note

The PostgreSQL service uses the PostgreSQL 18+ volume layout and mounts the named volume at `/var/lib/postgresql`.

If the local `postgres-data` volume was created from an earlier incorrect `/var/lib/postgresql/data` mount and you do not need to preserve that local data, recreate it with:

```bash
docker compose down -v
docker compose up --build
```
