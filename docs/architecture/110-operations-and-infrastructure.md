# Operations And Infrastructure

## Deployment Shape

The project is designed around a Docker Compose deployment rooted at the repository top level.

Planned services:

- `api`
- `web` during development
- `db`
- `nginx`
- certificate management service for ACME/TLS
- `db-backup`

The production and development layouts may differ slightly, but Compose remains the primary operational entry point.

## Backend Container

Current direction:

- Ubuntu Noble base image
- Python 3 runtime
- source mounted for reload-friendly development
- `uvicorn` used as the app server in development

Backend code quality expectations:

- full type hints
- linting via [`api/lint.sh`](/home/tfuller/git/goals/api/lint.sh)
- lint script runs `mypy`, `flake8`, and `ruff`

## Frontend Container

Current direction:

- Vue 3 plus Vite dev server
- source mounted for hot reload
- exposed to host during development on the planned frontend port

Build validation expectation:

- [`web/build.sh`](/home/tfuller/git/goals/web/build.sh) should validate TypeScript and production build viability

## Database

Current direction:

- PostgreSQL 18 container
- credentials sourced from environment variables
- bootstrap SQL in [`db/init.sql`](/home/tfuller/git/goals/db/init.sql) for initial user provisioning only
- schema creation and evolution owned by the Python application through Alembic

The database should persist:

- application data
- server-side sessions
- audit events
- notifications and reminder state
- seed application state

## Ingress And TLS

Nginx sits in front of the application stack.

Expected responsibilities:

- terminate TLS
- serve built frontend assets in production
- proxy API requests
- apply request shaping and rate limiting

Certificate handling direction:

- a separate service obtains and refreshes ACME certificates
- hostname and related configuration come from environment variables

## Backups

The project should include a dedicated backup service that periodically writes PostgreSQL backups into a mounted directory under `./backups`.

Current direction:

- backup ownership is controlled by configured UID and GID from environment
- backups are part of the normal Compose-managed environment
- restore procedures should eventually be documented once the stack exists

## Environment Configuration

The project should centralize deploy-time configuration in `.env` for Compose-driven values.

Expected configuration areas:

- database credentials
- session and app secrets
- TLS hostname and cert settings
- backup UID and GID
- any environment-specific ingress settings

## Operational Philosophy

This project is not targeting a complex HA deployment.

Operational design priorities are:

- maintainability
- local reproducibility
- safe restarts during development and testing
- simple observability when something breaks

This applies to reminder processing too. Scheduled reminder evaluation should be simple to reason about, easy to run locally, and visible enough to debug when reminders do or do not fire as expected.

## Future Documentation To Add

When implementation begins, this document should be extended with:

- exact Compose service definitions
- startup order requirements
- backup and restore procedures
- local development startup commands
- production deployment notes
