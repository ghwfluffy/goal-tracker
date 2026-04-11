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
- start date and optional target/end date
- timezone
- goal pattern

### Metric

A metric describes what kind of value the goal records.

Likely metric types:

- boolean completion
- numeric value
- count
- duration
- percent
- checklist progress

One goal may eventually support more than one metric, but the initial design should avoid unnecessary complexity unless a clear use case requires it.

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

### Derived State

Derived state is any recomputed result that is not the primary source record.

Examples:

- current completion percentage
- streaks
- on-track or at-risk indicators
- rolling-window score
- forecast output
- widget snapshot data

Derived state may be cached for performance, but it must be rebuildable.

### Dashboard

A dashboard is a saved layout that organizes widgets for a user.

### Widget

A widget is a saved visualization or summary configuration over one or more goals.

### Share Link

A share link exposes a widget or dashboard through a public identifier with controlled lifetime.

### Audit Event

An audit event records a meaningful action performed by a user or the system.

## Proposed Relationship Model

At a conceptual level:

- one user owns many goals
- one user owns many dashboards
- one user owns many widgets
- one goal has one or more rules
- one goal has one or more entries
- one widget references one or more goals
- one share link targets one widget or one dashboard
- one user has many sessions
- one user or system process emits many audit events

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
- rules
- entries
- dashboards
- widgets
- share links
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

### Keep auditability visible

Any entity that changes through system jobs should be designed so the resulting state can be correlated with audit events.

### Plan for controlled evolution

Since schema approval is still pending, the first schema proposal should map these concepts into a relational design and explain where polymorphism, enum use, and JSON fields are acceptable versus where stricter normalization is better.
