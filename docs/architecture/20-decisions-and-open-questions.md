# Decisions And Open Questions

## Approved Decisions

### Multi-user from the start

The application supports multiple users immediately. This is required because example/demo accounts and real accounts are both important early in the project.

Implications:

- data ownership must be explicit
- account management must not be bolted on later
- widgets, dashboards, and share links must have clear ownership

### No separate custom schema version tracker

Schema versioning will be owned by Alembic. The application will not maintain a second independent "dbversion" mechanism for schema state.

Implications:

- schema upgrade truth comes from Alembic only
- application configuration and feature flags belong in normal app tables
- seeded example-data evolution must be modeled separately from schema migration state

### No fully stateless signed session cookie design

The planned direction is to use server-side session persistence rather than a purely self-contained signed cookie.

Implications:

- sessions can be revoked cleanly
- password changes can invalidate sessions deterministically
- login continuity across normal container restarts is straightforward because session state lives in PostgreSQL

### Audit logging is part of the architecture

The system should preserve a durable audit trail for meaningful user and system actions, including future scheduled calculations that modify database state.

Implications:

- actions need actor and source metadata
- background jobs should record what they changed
- important write flows should be designed with auditability in mind

### Formal seeded example/demo data

Example data is a first-class system, not one-off bootstrap content.

Implications:

- flagged example/demo accounts receive deterministic seed content
- new features can add seed data to existing flagged accounts
- seeding needs its own upgrade mechanism

### Testing is a core design concern

The project should include backend tests, migration tests, frontend tests, and end-to-end smoke coverage as the system grows.

## Current Planned Decisions

These are strong current directions, but still worth confirming when the concrete schema is proposed.

### Session implementation

Planned direction:

- store sessions in PostgreSQL
- send an opaque signed or random session identifier in an HTTP-only cookie
- use normal expiration, revocation, and last-seen tracking

### Share-link design

Planned direction:

- share links use UUID-style public identifiers
- links may expire at a chosen time or never expire
- users can create, list, revoke, and inspect their links from profile/settings UI

### Seeded data upgrades

Planned direction:

- maintain seed profiles and seed revisions separately from Alembic revisions
- track which seed revisions have been applied to each flagged example-data account
- apply new feature seed content idempotently on upgrade

## Open Questions

These items should be proposed explicitly in the next approval round:

1. the exact schema and table relationships
2. the final goal, metric, rule, and entry boundaries
3. the first detailed phase plan beyond high-level sequencing
4. the first approved set of forecast algorithms
5. the final public-sharing permissions for widgets versus full dashboards
