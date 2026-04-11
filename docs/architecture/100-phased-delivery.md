# Phased Delivery

This document captures the current intended sequencing. It is not the final detailed roadmap yet.

## Planning Principle

The project should be delivered in multiple phases rather than treating everything as one oversized MVP.

The purpose of phasing is to:

- keep architecture decisions honest
- reduce schema churn
- make testing scope manageable
- get usable functionality early

## Phase 0: Foundation

Current intended scope:

- Docker Compose stack
- FastAPI and Vue project skeletons
- PostgreSQL integration
- Alembic setup
- auth/session foundation
- core testing scaffolding
- documentation baseline

## Phase 1: Core Goal Tracking

Current intended scope:

- account creation and login
- user profile basics
- user-owned metric creation and history tracking
- goal CRUD
- goal start-date semantics
- tags or basic categorization
- manual entry creation and editing
- goal history and status views
- responsive layouts for phone and desktop use in the core tracking flows
- first goal patterns:
  - habit completion
  - target value
  - task/checklist

Implemented so far in this phase:

- reusable user-owned metrics with integer/date value history
- quick metric entry updates from the signed-in shell
- goal creation backed by either an existing metric or a newly created inline metric

## Phase 2: Organization And Sharing

Current intended scope:

- dashboards
- saved widgets
- metric-history widgets
- in-app notifications and reminder generation
- share-link CRUD
- share-link expiration support
- profile/settings management for share links
- seeded example/demo user profiles and upgrade path
- admin backup inventory and on-demand backup creation

## Phase 3: Advanced Evaluation

Current intended scope:

- rolling-window allowance goals
- milestone and composite goal support where justified
- derived summaries
- initial forecast algorithms
- richer audit visibility

## Phase 4: Presentation And Polish

Current intended scope:

- server-side PNG widget rendering
- better public-share presentation
- richer dashboard composition
- operational polish around backups, maintenance, and observability
- admin restore workflow with confirmation UX and operational status visibility

## Not Yet Scheduled

These are intentionally not part of the near-term phased plan:

- third-party integrations
- separate native mobile clients
- collaborative cross-user goals
- mobile push notifications
- arbitrary formula builders

## Next Planning Step

The next design round should replace this high-level phase list with a more concrete plan that ties features to schema dependencies, testing requirements, and migration risk.
