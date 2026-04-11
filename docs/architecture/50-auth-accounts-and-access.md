# Auth, Accounts, And Access

## Goals

The auth design should be simple, maintainable, and durable across normal container restarts used during development and testing.

## Account Model

The current plan includes:

- normal user accounts
- administrator accounts
- example/demo accounts

The first created account is intended to become an administrator. After that, user creation should be controlled by registration policy and admin tooling.

## Registration Direction

Current planned behavior:

- first account can be created without a registration code
- later registration should require an admin-managed registration code
- registration codes should carry expiration timestamps and remain traceable to the users created with them
- invited registration should allow a user to opt into the example/demo account path
- admins can manage user accounts

This area should remain simple until real usage requires more complexity.

## Session Design

The project will not use a fully stateless signed-cookie session model.

Planned design:

- create a server-side session record in PostgreSQL
- issue an opaque cookie value that references the session
- keep cookie HTTP-only and secure in production
- enforce expiration server-side
- support revocation and password-change invalidation cleanly

Why this direction:

- easier revocation
- easier auditability
- better fit for admin actions
- durable across container restarts as long as the database persists
- clean password storage using bcrypt-backed hashes with production-safe work factors

## Session Lifecycle

Each session should support:

- creation time
- last-seen time
- expiration time
- revocation time
- optional metadata such as user agent or source IP summary

The system should be able to list and revoke active sessions later if desired, even if that UI does not ship immediately.

## Access Model

Default access rules:

- users can manage their own goals, dashboards, widgets, share links, and profile
- admins can perform administrative account and registration-code operations
- admins can create backups, inspect backup inventory, and initiate restore workflows
- public access is only through explicit share-link records

## Media And User Input Safety

The current design direction remains:

- validate and sanitize all user input
- process uploaded profile images through controlled resizing and PNG re-rendering
- keep upload handling conservative and explicit

## Security Notes

- secrets come from environment variables
- session signing or cookie protection keys should never silently use unsafe defaults in production
- rate limiting remains an ingress concern at Nginx
- auth flows and privileged writes should generate audit events
- restore actions should require stronger confirmation than normal CRUD, and the architecture should assume admin-only access plus explicit server-side validation before any destructive step runs
