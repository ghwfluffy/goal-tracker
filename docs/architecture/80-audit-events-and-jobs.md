# Audit, Events, And Jobs

## Purpose

The project should preserve a durable audit trail of meaningful system actions. This includes user-submitted changes and future automated processes that modify database state.

## What Should Be Audited

Examples of actions that should generate audit records:

- account creation
- login and logout events where practical
- password changes
- admin actions on users or registration codes
- goal creation, update, archival, completion, and deletion
- entry creation and correction
- share-link creation and revocation
- seed-data application and seed upgrades
- background calculations that persist derived state

Not every read action needs auditing. The goal is meaningful traceability, not noise.

## Audit Event Shape

The exact schema is not finalized, but each audit record should be able to answer:

- who performed the action
- whether it was user-driven or system-driven
- what entity or entities were affected
- what action occurred
- when it occurred
- enough context to explain the write without storing unsafe secrets

## Actor Model

Expected actor categories:

- authenticated user
- administrator acting as admin
- system process
- background job

## Background Jobs

The initial application may not need many scheduled jobs, but the design should leave room for them.

Likely future jobs:

- forecast recalculation
- derived summary refresh
- share-link expiration cleanup
- backup or maintenance reporting hooks
- seed-data upgrade runner

## Job Rules

When jobs change persistent state:

- the change should be deterministic where possible
- the job should emit audit records
- failures should be diagnosable
- reruns should be safe

## Relationship To Derived State

If the system persists cached summaries or forecast data, those writes should be treated as system-generated derived writes. The audit trail should make it possible to distinguish these from direct user inputs.
