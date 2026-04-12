# Backend Python Modularization

This guide documents how backend Python code in Goal Tracker should be organized so the FastAPI + service + SQLAlchemy structure stays easy to extend.

Use this alongside the architecture docs in [`docs/architecture`](../architecture/README.md). Architecture documents decide system shape and product rules. This guide explains how to express those decisions cleanly in code.

## Goals

- keep route modules focused on HTTP concerns
- keep business rules in reusable service modules
- keep persistence models in the database layer
- avoid duplicated logic across routes, services, and widgets
- split files before they become multi-purpose dumping grounds

## Current Backend Shape

The backend should generally stay in these layers:

- `api/app/api/routes`
  FastAPI routers, request handling, response codes, and dependency wiring.
- `api/app/api/schemas`
  Pydantic request and response models plus serializer helpers when a route would otherwise become too large.
- `api/app/services`
  Business rules, validation, orchestration, and reusable domain logic.
- `api/app/db`
  SQLAlchemy models and session plumbing.

Do not move domain rules into route modules just because the first endpoint is small. Prefer the target shape from the start.

## Route Module Rules

Route files should mostly do four things:

1. parse validated request payloads
2. load authenticated user and database session dependencies
3. call service-layer functions
4. translate domain errors into HTTP errors

Route modules should not become the home for:

- repeated serializer logic shared by multiple endpoints
- non-trivial progress calculations
- layout or forecasting rules
- cross-endpoint validation that belongs to the domain

If a route file starts mixing endpoint handlers, many schema classes, and many serializer helpers, split the schemas and serializers into `api/app/api/schemas/<domain>.py`.

## Service Module Rules

Service modules are the source of truth for domain behavior.

Good service responsibilities:

- validating domain invariants
- normalizing user input for persistence
- calculating progress, forecasts, or compliance
- coordinating related writes in a transaction
- loading related records needed by the domain operation

Avoid these service smells:

- duplicated helper functions across multiple services
- modules that mix unrelated domains
- service functions that return HTTP-specific errors or response objects
- business rules implemented differently in goal views and dashboard views

When two domains use the same rule, extract a focused shared module in `api/app/services`. Examples:

- goal progress math
- shared datetime normalization
- dashboard layout validation
- reusable loading options or query helpers

The extracted module should be narrow and named after the capability it owns, not after a vague concept like `utils`.

## Database Layer Rules

Keep SQLAlchemy models in `api/app/db/models.py` unless the file becomes hard to navigate. If the model file grows further, split by domain while preserving a single import surface through `api/app/db/__init__.py`.

Database modules should not absorb:

- endpoint serialization
- business workflows
- request validation rules that do not depend on mapping metadata

## Reuse Rules

Shared code should be reused from one authoritative place.

Prefer this order:

1. existing domain service helper
2. new focused shared service module
3. local helper inside one module

Avoid copying a helper just because importing it feels inconvenient. If import boundaries feel awkward, the module boundaries likely need adjustment.

Before adding a new helper, check whether the same logic already exists for:

- timezone conversion
- recorded-at normalization
- goal progress calculations
- decimal and numeric normalization
- widget layout validation
- object serialization

## File Size Guidance

There is no single magic line count, but these thresholds are a useful warning system:

- under ~200 lines: usually fine
- 200 to 350 lines: review for mixed responsibilities
- above ~350 lines: split unless the file is truly one coherent unit
- above ~500 lines: treat as a refactor target

Also split earlier when a file:

- contains more than one domain concept
- mixes CRUD, calculations, and serialization
- repeats patterns already present elsewhere
- is hard to skim top-to-bottom in one pass

## Extension Checklist

When adding backend behavior:

1. confirm the change matches the architecture docs
2. decide the owning domain module before writing code
3. put HTTP-only types in route or schema modules
4. put business rules in services
5. extract shared logic instead of copying it
6. add or update tests for the new behavior
7. run `./scripts/validate.sh`

## Preferred Style

- prefer small typed functions with explicit parameters
- keep validation messages close to the rule they enforce
- use descriptive names over generic helpers
- favor narrow imports and domain-focused modules
- keep backend Python files within the enforced 110-column line width
- add brief comments only when the intent is not obvious from the code

## What To Avoid

- `helpers.py`, `misc.py`, `common.py`, or `utils.py` as catch-all modules
- route modules that compute domain values directly
- duplicated serializer code across multiple route files when the payload shape is shared
- service modules that silently diverge on the same business rule
- broad refactors that change behavior without tests proving the intended result
