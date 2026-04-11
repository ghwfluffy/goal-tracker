# Goal Engine

## Purpose

The goal engine is the part of the system that interprets entries and rules into meaningful status for users.

The design should support varied goal patterns while keeping behavior explainable.

## First-Class Goal Patterns

The current planned first-class patterns are:

- habit completion
- target value
- task completion with optional checklist
- rolling-window allowance
- milestone sequence
- composite goal

Not all of these must ship in the first implementation phase, but the model should leave room for them.

## Schedule Semantics

Goals that depend on time or cadence need explicit schedule semantics.

Expected schedule fields:

- timezone
- cadence
- selected weekdays when relevant
- optional target/end date
- backfill policy
- grace window for late confirmation
- exception dates or exception windows

## Occurrence States

For scheduled goals, the system should distinguish:

- `done`
- `missed`
- `skipped`
- `unknown`

This prevents missing data from being treated as failure by default.

## Entry Philosophy

Entries are the primary user input mechanism.

Expected entry capabilities:

- create a new update
- backfill an update for a prior date if allowed
- attach a note explaining context
- distinguish manual entries from system-generated records
- preserve an audit trail of changes

## Progress Evaluation

The system should compute progress differently depending on goal pattern:

### Habit completion

Evaluate whether required occurrences were completed in the relevant time window.

### Target value

Evaluate current value against target, start value, and optional target date.

### Task completion

Evaluate completion from explicit final status and optional subtasks.

### Rolling-window allowance

Evaluate recent behavior over the last `N` days or occurrences and compute a compliance score.

### Milestone sequence

Evaluate based on completion of ordered checkpoints.

### Composite goal

Evaluate as a weighted or rule-based combination of other goals.

## Forecasting

Forecasting is planned as a pluggable subsystem, not hard-coded into each goal type.

Each forecast algorithm should declare:

- algorithm identifier
- supported metric types
- minimum required history
- output time series
- confidence or reliability summary
- explanation text suitable for the UI

Planned starting algorithms:

- simple linear trend
- rolling average delta
- weekday-weighted numeric forecast
- explicit no-forecast result when data is insufficient

## Derived State And Caching

The engine may persist rebuildable derived records for performance, but those records should never become the only source of truth.

Candidate cached outputs:

- daily or weekly summaries
- current status snapshot
- streak counts
- rolling-window compliance summaries
- forecast series

## Design Constraints

- the system must stay understandable to the user
- hidden algorithmic magic should be avoided
- rules should be deterministic given the same inputs
- calculations that modify stored derived state should emit audit events
