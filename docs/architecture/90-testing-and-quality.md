# Testing And Quality

## Testing Philosophy

Testing is part of the project design, not cleanup after implementation.

The system should maintain confidence at four levels:

- backend logic and APIs
- migration and upgrade safety
- frontend components and flows
- end-to-end smoke coverage

## Backend Tests

Planned tools:

- `pytest`
- FastAPI test tooling
- `httpx`

Coverage priorities:

- auth flows
- goal creation and editing
- entry submission and validation
- reminder generation logic
- share-link management
- seed-data application logic
- audit-event generation for important writes

## Migration Tests

The project should test schema upgrades on disposable PostgreSQL databases.

Coverage priorities:

- upgrade from prior revisions
- compatibility of new schema with existing data
- interaction between schema upgrades and seed-data upgrades

## Frontend Tests

Planned tools:

- `vitest`
- Vue Test Utils

Coverage priorities:

- goal creation/editing forms
- entry flows
- notification display and reminder preference flows
- dashboard and widget management
- share-link management UI
- auth/session-aware navigation behavior

## End-To-End Tests

Planned tool:

- Playwright

Early smoke coverage should validate:

- login
- create goal
- submit entry
- receive or observe a due reminder in a deterministic test case
- view dashboard
- create or revoke share link

## Linting And Type Safety

Current repo direction:

- backend lint script runs mypy, flake8, and ruff
- frontend build script validates TypeScript and production build viability

These checks should be run routinely during implementation work.

## Fixture Strategy

The test system should reuse the same deterministic example-data concepts where useful, but test fixtures must stay isolated and purpose-built.

Recommended fixture categories:

- minimal auth fixture
- single-user goal fixture
- multi-user ownership boundary fixture
- reminder-due fixture
- example/demo seeded user fixture
- migration fixture for historical revisions

## Quality Principle

When a feature adds new persistent behavior, the expected test additions should include:

- direct backend logic coverage
- API behavior coverage
- relevant frontend coverage when user-facing
- migration or seed-upgrade coverage when persistence behavior changes
