# Seeded Data And Data Evolution

## Purpose

The project needs deterministic example/demo data for development, testing, screenshots, and onboarding. It also needs a safe way to extend that data when new features ship.

This is separate from schema migration.

## Core Design

The system should treat seed data as a formal application feature.

Expected behaviors:

- create example/demo content for flagged users
- apply deterministic seed profiles
- evolve seed content when new features are introduced
- do so idempotently so upgrades are safe to rerun

## Why This Is Separate From Alembic

Alembic should own schema evolution only.

Seeded data evolution is different because:

- it depends on application semantics, not just table structure
- it should target only flagged example/demo accounts
- it may need conditional behavior when a feature is introduced later

## Planned Model

The current design direction is:

- maintain named seed profiles such as `basic`, `fitness`, or `finance`
- maintain a seed revision history at the application level
- mark example/demo accounts in the database
- track which seed revisions have been applied to which flagged accounts
- run an upgrader that applies newly introduced seed revisions to all existing flagged example/demo accounts

## Upgrade Flow

When a new feature adds example content:

1. Alembic upgrades the schema if needed.
2. The application seed upgrader discovers flagged example/demo accounts.
3. It applies any new unapplied seed revisions for the relevant seed profile.
4. It records the applied seed revision.
5. It emits audit events describing what seed changes were made.

## Idempotency Requirements

Seed application must be idempotent.

That means:

- rerunning the process should not duplicate records
- seed records should have stable identifiers or stable lookup rules
- partial failures should be recoverable

## What Seed Data Should Include

The seed system should eventually be able to create:

- users flagged for example/demo use
- standalone metric histories
- goals
- entries
- widgets
- dashboards
- share-link examples only if clearly safe and intentionally scoped

Public share links should not be seeded casually because they create visibility outside the normal private boundary.

## Design Constraint

The seed system should never be allowed to overwrite real-user data. It applies only to flagged example/demo accounts or to explicitly invoked development fixtures.
