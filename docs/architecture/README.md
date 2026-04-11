# Architecture Docs

This directory captures the current planned architecture for the goal tracker project.

These documents are intended to answer two questions:

1. what has already been decided
2. what still needs explicit approval before implementation locks it in

## Document Map

- [System Overview](./10-system-overview.md)
- [Decisions And Open Questions](./20-decisions-and-open-questions.md)
- [Domain Model](./30-domain-model.md)
- [Goal Engine](./40-goal-engine.md)
- [Auth, Accounts, And Access](./50-auth-accounts-and-access.md)
- [Dashboards, Widgets, And Sharing](./60-dashboards-widgets-and-sharing.md)
- [Seeded Data And Data Evolution](./70-seeded-data-and-data-evolution.md)
- [Audit, Events, And Jobs](./80-audit-events-and-jobs.md)
- [Testing And Quality](./90-testing-and-quality.md)
- [Phased Delivery](./100-phased-delivery.md)
- [Operations And Infrastructure](./110-operations-and-infrastructure.md)

## Current Design State

Approved direction so far:

- multi-user support from the start
- no separate custom schema version tracker
- no fully stateless signed session cookie design
- audit logging is part of the system design
- seeded example/demo data is a formal system, not ad hoc scripts
- test strategy should include backend, migrations, frontend, and end-to-end layers

Still intentionally not locked:

- the exact relational schema
- the final entity boundaries and table layout
- the detailed phase plan after phase 0 and phase 1

Until those are approved, implementation should treat the entity model in these docs as a proposed architecture model, not a frozen schema contract.
