# Goal Engine

## Purpose

The goal engine is the part of the system that interprets entries and rules into meaningful status for users.

The design should support varied goal patterns while keeping behavior explainable.

It should also distinguish between:

- long-lived user metric history
- goal-specific evaluation over that history

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

- required goal start date
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

Occurrences should only be evaluated on or after the goal start date.

## Entry Philosophy

Entries are the primary user input mechanism.

Expected entry capabilities:

- create a new update
- backfill an update for a prior date if allowed
- attach a note explaining context
- distinguish manual entries from system-generated records
- preserve an audit trail of changes

For metrics such as `weight`, entries should usually attach to the user-owned metric stream first, with goals consuming that metric history as needed.

## Shared Metrics Versus Goal-Bound Data

Not every tracked value should be owned only by a goal.

Recommended model:

- long-lived user metrics store historical measurements or states
- goals reference those metrics when the goal is about improving, reducing, or maintaining that metric
- some goal patterns may still need goal-bound entries, especially checklist or one-off task flows

Examples:

- `weight` should be a reusable user metric referenced by multiple present or future goals
- a "reach 100 lbs" goal should evaluate progress from the `weight` metric history
- a widget should be able to show the `weight` metric history even when no weight goal is active
- a one-off task completion goal may not need a reusable standalone metric at all

## Goal Start Date Semantics

Goal start dates are first-class, required fields.

Expected effects:

- goal schedule generation starts at the start date
- progress windows should not penalize the user before the goal starts
- reminders begin only when the goal is active
- target-date calculations use the start date as the beginning of the planned goal interval unless a goal pattern defines a different baseline

## Progress Evaluation

The system should compute progress differently depending on goal pattern:

### Habit completion

Evaluate whether required occurrences were completed in the relevant time window.

### Target value

Evaluate current value against target, start value, and optional target date, typically using a referenced metric stream.

### Task completion

Evaluate completion from explicit final status and optional subtasks.

### Rolling-window allowance

Evaluate recent behavior over the last `N` days or occurrences and compute a compliance score.

### Milestone sequence

Evaluate based on completion of ordered checkpoints.

### Composite goal

Evaluate as a weighted or rule-based combination of other goals.

## Reminder Inputs From The Goal Engine

The goal engine should expose enough derived information for the reminder system to know when a user action is still outstanding.

Examples:

- today’s occurrence is still `unknown`
- today’s expected metric entry has not been submitted
- a weekly task remains incomplete near the end of its allowed window

The reminder system should consume this state without changing the underlying completion logic.

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

## Metric History As A First-Class Output

The system should treat raw and lightly processed metric history as a first-class thing users can inspect.

That means the product should support:

- viewing metric history outside any specific goal
- rendering widgets directly from metric series
- reusing the same metric data across successive goals

## Design Constraints

- the system must stay understandable to the user
- hidden algorithmic magic should be avoided
- rules should be deterministic given the same inputs
- calculations that modify stored derived state should emit audit events
