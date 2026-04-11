# Domain Model

This document describes the proposed conceptual model for the system. It is intentionally not the final approved schema.

## Core Concepts

### User

Represents an account that can log in, own data, manage profile settings, and create share links.

Expected responsibilities:

- authenticate
- own goals, dashboards, widgets, sessions, and share links
- optionally be marked as administrator
- optionally be marked as an example-data account

### Goal

A goal is the user-facing object representing an objective.

Expected attributes:

- owner
- title
- description
- category or tag assignments
- status such as active, paused, archived, completed
- required start date and optional target/end date
- timezone
- goal pattern
- optional link to one or more user-owned metrics used by the goal
- optional reminder configuration

### Metric

A metric describes a user-owned stream of tracked values or states that may be reused across time and across multiple goals.

Examples:

- `weight`
- `cardio_minutes`
- `tv_watch_flag`
- `sleep_hours`
- `daily_steps`

Likely metric types:

- boolean completion
- numeric value
- count
- duration
- percent
- checklist progress
- performance measurement such as elapsed time for a fixed-distance effort

Important design direction:

- a metric may exist even when no goal is active
- a goal may reference an existing metric rather than owning the entire history itself
- one goal may eventually support more than one metric, but the initial design should avoid unnecessary complexity unless a clear use case requires it
- a metric may have multiple timestamped entries on the same day, such as morning and evening weight measurements or multiple rowing attempts

### Rule

A rule describes how progress is interpreted from entries.

Examples:

- do at least once per day
- stay under a threshold
- reach a target value
- satisfy a rolling-window allowance
- complete all checklist items

### Entry

An entry is source data supplied by a user or system process.

Expected characteristics:

- timestamped
- attributed to an actor or system source
- may contain note text
- may contain attached file or image references later
- should support edit history or replacement tracking
- should be attributable to one or more metric streams and optionally to a goal context
- should preserve exact measurement time so multiple same-day entries remain distinct
- may include attempt metadata when the entry represents a performance effort or workout attempt

### Reminder Configuration

Reminder configuration describes when the system should remind a user to take an expected action.

Possible attachment points:

- goal-level reminder settings
- metric-level reminder settings
- user-level notification defaults

Examples:

- remind me at 8:00 PM if I have not marked cardio complete
- remind me every morning to enter my weight
- remind me if a weekly task has not been updated by Sunday evening

### Notification

A notification is a user-visible reminder or system message generated from reminder rules or other important application events.

Expected characteristics:

- owned by a user
- tied to a source such as a goal, metric, or system event
- has a generated time
- has a state such as pending, delivered, read, dismissed, expired, or failed
- may record delivery channel and delivery attempts

### Derived State

Derived state is any recomputed result that is not the primary source record.

Examples:

- current completion percentage
- streaks
- on-track or at-risk indicators
- rolling-window score
- forecast output
- widget snapshot data
- best-attempt summaries for performance goals

Derived state may be cached for performance, but it must be rebuildable.

### Dashboard

A dashboard is a saved layout that organizes widgets for a user.

### Widget

A widget is a saved visualization or summary configuration over one or more goals, one or more metrics, or both.

### Share Link

A share link exposes a widget or dashboard through a public identifier with controlled lifetime.

### Audit Event

An audit event records a meaningful action performed by a user or the system.

### Backup Snapshot

A backup snapshot represents a known backup artifact that administrators can inspect and potentially restore from.

Expected characteristics:

- stable identifier
- creation time
- source type such as scheduled or on-demand
- storage location or opaque storage reference
- size and retention metadata where available
- status such as pending, completed, failed, expired, or deleted
- actor when user-triggered

### Restore Operation

A restore operation represents an explicit administrative request to restore application state from a backup snapshot.

Expected characteristics:

- references a target backup snapshot
- initiated by an administrator
- has requested, started, completed, failed, or cancelled states
- stores confirmation metadata and reason text where required
- records result details sufficient for operations and audit review
- may reference pre-restore safety actions such as creating a fresh backup before restore

## Proposed Relationship Model

At a conceptual level:

- one user owns many goals
- one user owns many metrics
- one user owns many dashboards
- one user owns many widgets
- one user owns many notifications
- one administrator may initiate many backup snapshots and restore operations
- one metric has many entries
- one goal has one or more rules
- one goal may have reminder configuration
- one metric may have reminder configuration
- one goal may reference one or more metrics
- one goal may have one or more entries or derived occurrences in goal-specific cases
- one widget references one or more goals, metrics, or both
- one share link targets one widget or one dashboard
- one user has many sessions
- one user or system process emits many audit events
- one backup snapshot may have many restore operations over time

## Ownership Model

The default ownership rule is simple:

- users can access their own private records
- public access exists only through explicit share-link records
- administrative powers should not imply blanket public visibility

## Data Classification

### Source-of-truth records

- users
- sessions
- goals
- metrics
- rules
- entries
- reminder configuration
- notifications
- dashboards
- widgets
- share links
- backup snapshots
- restore operations
- audit events
- seed application records

### Derived and rebuildable records

- daily summaries
- cached progress state
- forecast series
- image render caches
- dashboard materializations

## Modeling Notes

### Avoid table-per-goal-type if possible

The current direction is to support multiple goal patterns from common primitives. The schema should only split into specialized tables where the common model becomes unnatural or unreadable.

### Keep metric history independent from goal lifecycle

A long-lived metric like `weight` should survive before, during, and after any specific goal that references it. Goal completion or archival should not imply loss of the underlying metric history.

### Keep reminder semantics separate from progress semantics

Reminder rules should influence when the user is notified, not what the system considers completed or compliant. A missed reminder is not automatically a failed goal occurrence.

### Keep auditability visible

Any entity that changes through system jobs should be designed so the resulting state can be correlated with audit events.

### Treat restore as an explicit operational domain concept

Restore should not be an undocumented shell-side escape hatch. If the UI can request restore behavior, the domain model needs first-class records for backup inventory and restore execution history so the system can explain what happened, who requested it, and what source artifact was used.

### Plan for controlled evolution

Since schema approval is still pending, the first schema proposal should map these concepts into a relational design and explain where polymorphism, enum use, and JSON fields are acceptable versus where stricter normalization is better.
