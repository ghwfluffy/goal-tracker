# Agent Instructions

- Keep the architecture aligned with the documents in [`docs/architecture`](./docs/architecture/README.md).
- Run `./scripts/validate.sh` after code changes unless the task explicitly does not require it.
- Keep [`README.md`](./README.md) customer-facing and understandable to non-technical readers; move implementation-heavy details into docs instead of turning the README into internal setup notes.
- Maintain [`README.md`](./README.md) and relevant docs when high-level behavior or developer workflow changes.
- Prefer small, typed, test-backed changes that preserve the FastAPI + Vue + PostgreSQL shape of the project.
