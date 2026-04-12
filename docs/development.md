# Development Flow

This document captures the current implemented developer workflow for the Phase 0 foundation.

Coding-style guidance and style-change notes now live in:

- [`docs/style`](./style/README.md)
- [`docs/style/backend-python-modularization.md`](./style/backend-python-modularization.md)

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
4. `POST /api/v1/auth/register`
5. `GET /api/v1/auth/me`
6. `POST /api/v1/auth/logout`
7. `GET /api/v1/invitation-codes`
8. `POST /api/v1/invitation-codes`
9. `PATCH /api/v1/invitation-codes/{invitation_code_id}`
10. `DELETE /api/v1/invitation-codes/{invitation_code_id}`
11. `GET /api/v1/metrics`
12. `POST /api/v1/metrics`
13. `POST /api/v1/metrics/{metric_id}/entries`
14. `GET /api/v1/goals`
15. `POST /api/v1/goals`
16. `PATCH /api/v1/goals/{goal_id}`
17. `GET /api/v1/dashboards`
18. `POST /api/v1/dashboards`
19. `PATCH /api/v1/dashboards/{dashboard_id}`
20. `DELETE /api/v1/dashboards/{dashboard_id}`
21. `POST /api/v1/dashboards/{dashboard_id}/widgets`
22. `PATCH /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}`
23. `DELETE /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}`

The first account bootstrap path creates the initial administrator and starts a server-side session using an HTTP-only cookie. After that, new users register through admin-managed invitation codes and can opt into example-data seeding at signup. Example-data accounts now receive a deterministic starter set of metrics, richer historical entries, goals, and a dashboard that exercises multiple widget types, and the app tracks applied seed revisions so existing flagged example accounts can be upgraded when new seed content is added. The example-data upgrader runs both at FastAPI startup and during auth flows so restarting the server is enough to backfill newly introduced seed revisions. Passwords are stored with bcrypt-backed hashes. Each user also has a persisted IANA timezone setting for day-boundary semantics, defaulting to `America/Chicago`, while timestamps remain stored in UTC.

The frontend home page now consumes that auth foundation and can:

1. detect whether bootstrap is still required
2. create the first administrator account
3. sign in with an existing account
4. register a new invited account with an optional example-data flag
5. restore the current session
6. sign out
7. let administrators create, update, review, and revoke invitation codes
8. create reusable number/date metrics with configurable decimal places, editable reminder times, and add quick updates
9. archive metrics so they are hidden by default, or permanently delete standalone metrics that are not used by goals or widgets
10. create and edit goals tied to an existing metric or a new inline metric, including date-based compliance goals with exception dates and success thresholds
11. archive goals so they are hidden by default and can be restored when needed
12. create dashboards, choose a default dashboard, and manage dashboard widgets in a dedicated edit mode, including target-date goal charts plus completion, success, and risk widgets
13. surface due metric reminders through a notification bell with quick entry and skip actions
14. render widget timestamps in the browser timezone while showing the saved profile timezone used for day-boundary logic

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

Keep Alembic `revision` ids at 32 characters or fewer. PostgreSQL stores the active revision in
`alembic_version.version_num`, and longer ids will fail during `alembic upgrade head`.

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
