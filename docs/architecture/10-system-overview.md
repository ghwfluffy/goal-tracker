# System Overview

## Purpose

The project is a web application for tracking personal goals through manual updates, progress evaluation, dashboards, notifications/reminders, and future forecasting. It is intended to support multiple users from the beginning, including real accounts and example/demo accounts.

The system should feel flexible enough to support very different goal types without turning into a separate product for each one.

## Product Shape

The product centers on a few ideas:

- users define goals
- users submit entries against those goals
- the system derives progress, status, and summaries from those entries
- the system reminds users when expected actions have not been completed
- dashboards and widgets present the current state
- selected widgets can be shared through revocable public links
- administrators can manage backups and controlled restores through the application UI

## Scope Direction

The design favors:

- strong manual tracking support first
- reusable internal primitives over one-off goal implementations
- explainable calculations and forecasts
- maintainable infrastructure over theoretical HA complexity
- durable documentation so future agents can understand why things were built a certain way

The design does not currently prioritize:

- mobile apps
- third-party data imports
- advanced collaborative/team workflows
- mobile push notification systems
- highly advanced forecasting in the first delivery phases

## High-Level Technical Architecture

### Runtime components

- `web`: Vue 3 SPA served in development by Vite
- `api`: Python FastAPI application that owns business logic and database access
- `db`: PostgreSQL database
- `nginx`: ingress layer for TLS, static asset serving in production, and request shaping
- `db-backup`: periodic backup service writing to mounted backup storage

### Development topology

- Docker Compose at repo root orchestrates the stack
- source directories are mounted into containers for hot reload
- backend reload is handled by `uvicorn --reload`
- frontend reload is handled by Vite dev server

### Planned backend stack

- Python 3 on Ubuntu Noble container
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- Uvicorn

### Planned frontend stack

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- PrimeVue

## System Boundaries

The API owns:

- auth and session handling
- goal definitions
- entries and progress logic
- notification and reminder logic
- widget and dashboard persistence
- share link management
- backup catalog, restore request handling, and operational guardrails
- audit logging
- example-data seeding and seed upgrades

The frontend owns:

- interactive creation and editing flows
- data presentation
- notification display and reminder-management UX
- dashboard composition UX
- share-link management UI
- admin backup and restore UX

The database owns:

- durable source-of-truth state
- server-side session persistence
- audit/event history
- notification state and reminder configuration
- backup metadata and restore-operation history
- seed version state for flagged example-data accounts

## Architectural Principles

### Source data first

User-entered history is the core source of truth. Derived views such as streaks, rolling-window summaries, projections, and widget snapshots should be rebuildable from source data plus deterministic rules.

### Explainable state

When the system computes status, projections, or scheduled outcomes, it should be possible to understand why that state exists.

### Multi-user isolation

Ownership boundaries should be first-class from the start. User-private data should stay private unless explicitly shared.

### Controlled public sharing

Public sharing should happen through explicit share-link records, not by exposing internal identifiers or private routes.

### Operational simplicity

This project does not need complex distributed systems behavior. A straightforward single-database design is preferred if it remains maintainable and testable.

### Admin-driven recoverability

Backups and restores should be operationally simple, visible, and intentionally gated. The architecture should support admin-only UI flows for listing backups, creating on-demand backups, and initiating controlled restore operations with strong auditability and clear safeguards.
