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

### User-level shared metrics

The system should support user-owned metrics that can exist independently of any currently active goal.

Implications:

- a metric such as `weight` should be tracked continuously over time
- multiple goals may reference the same underlying metric history
- widgets should be able to render metric history directly, without requiring a goal wrapper
- goals should consume metric history rather than forcing each goal to own a separate isolated series

### Goals have explicit start dates

Goals should have explicit start dates, not just optional end dates.

Implications:

- schedule generation begins at the goal start date
- occurrences before the start date should not count toward compliance
- reminders for a goal should not begin before the start date
- metric history may predate the goal, but goal evaluation windows begin at the goal start date unless the goal pattern explicitly says otherwise

### Date-only end dates resolve to end-of-day

When a goal is configured with a date-only target or end date, that deadline should be interpreted as end-of-day in the goal's timezone rather than the start of that day.

Implications:

- a goal such as "240 lbs by April 30" remains active through the end of April 30 in the goal timezone
- a daily cadence goal "until April 30" includes April 30 as an evaluable day
- reminder and status logic must use the goal timezone when resolving date-only deadlines

### Notifications and reminders are part of the product

The system should remind users about expected actions such as marking a daily goal complete or entering a metric value.

Implications:

- reminders must work for both goal-driven tasks and standalone metric-entry expectations
- reminder generation needs user timezone awareness
- notification state and delivery attempts should be modeled explicitly
- background jobs will need to evaluate what reminders are due

### Formal seeded example/demo data

Example data is a first-class system, not one-off bootstrap content.

Implications:

- flagged example/demo accounts receive deterministic seed content
- new features can add seed data to existing flagged accounts
- seeding needs its own upgrade mechanism

### Testing is a core design concern

The project should include backend tests, migration tests, frontend tests, and end-to-end smoke coverage as the system grows.

### Backup and restore are admin capabilities

Backup creation, backup listing, and controlled restore flows are part of the architecture and should be available through the administrator UI, not only through direct container or shell access.

Implications:

- backup and restore actions need explicit authorization checks
- restore workflows need strong confirmation and safety rules
- backup inventory and restore history need durable records
- these flows must produce meaningful audit events

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

### Metric architecture

Planned direction:

- separate long-lived user metric history from goal-specific evaluation rules
- allow goals to reference an existing metric stream such as `weight`
- allow widgets to visualize the metric stream even when no goal is currently active
- metric streams support multiple timestamped entries on the same day rather than forcing one value per day

### Notification delivery

Planned direction:

- support in-app notifications/reminders as a first-class feature
- design the notification model so additional channels such as email can be added later
- keep reminder scheduling deterministic and auditable

### Performance-attempt goals

Planned direction:

- the architecture should support goals evaluated from repeated performance attempts, such as rowing 2km under a target time
- the underlying metric history stores every attempt with its exact timestamp and measured value
- the rule layer decides whether goal status is based on best attempt, latest attempt, rolling average, or another explicit evaluation rule

### Backup and restore workflow

Planned direction:

- a backup service continues to create scheduled database backups to mounted storage
- the application stores backup metadata records so admins can inspect available backups in the UI
- admins can trigger an on-demand backup from the UI
- admins can initiate a controlled restore workflow from the UI, with the actual restore executed by a privileged backend or maintenance path rather than by arbitrary browser-side behavior
- restore operations should be modeled as explicit jobs with status, actor, timestamps, and result details

## Open Questions

These items should be proposed explicitly in the next approval round:

1. the exact schema and table relationships
2. the final goal, metric, rule, and entry boundaries
3. the first detailed phase plan beyond high-level sequencing
4. the first approved set of forecast algorithms
5. the final public-sharing permissions for widgets versus full dashboards
6. the exact notification/reminder schema and delivery model
7. the exact safety model for restore execution, such as full-instance restore only versus scoped restore support
