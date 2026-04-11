# Agent Thoughts

These are additional design refinements based on `./docs/INITIAL-THOUGHTS.md`. The goal here is to keep the product flexible without letting the implementation turn into a pile of one-off goal types.

## 1. Model the system around reusable tracking primitives

Instead of hard-coding many separate goal categories, define a small set of primitives that can be combined:

- `goal`: the user-facing objective, title, description, category, owner, visibility, timezone, start/end dates
- `metric`: what is being tracked, such as boolean completion, numeric value, count, duration, percent, or checklist progress
- `entry`: a timestamped user update with optional note, source, and confidence
- `rule`: how progress is evaluated, such as daily completion, rolling-window allowance, target threshold, milestone list, or weighted score
- `forecast`: optional algorithm output derived from entries, not user-authored source data
- `widget`: a saved visualization configuration over one goal or many goals

This lets the app support cardio, weight, task completion, and "avoid TV except on allowed days" without needing a totally different storage model for each one.

## 2. Separate source data from derived progress

A useful design boundary is:

- Source data is immutable user-entered history.
- Derived data is recalculated progress, streaks, rolling-window scores, forecasts, and dashboard summaries.

That means a user can edit an old check-in, and the system recomputes the downstream status instead of storing conflicting denormalized state everywhere. For performance, derived daily snapshots or cached aggregates can still exist, but they should be rebuildable.

## 3. Distinguish `missed`, `skipped`, and `unknown`

This matters for habit-style goals. A day with no entry is not always the same as failure.

Recommended states for scheduled goal occurrences:

- `done`: confirmed completed
- `missed`: confirmed not completed
- `skipped`: intentionally excluded by rule, such as rest day or approved exception
- `unknown`: no confirmation yet

Without this distinction, streaks and rolling-window scores will become misleading.

## 4. Make schedule semantics explicit

Several of your examples depend on scheduling logic. Each goal should be able to declare:

- timezone
- cadence: daily, weekly, selected weekdays, monthly, ad hoc
- backfill policy: whether old dates can be edited
- grace window: when a day is considered closed
- exception dates: holidays, illness, travel, special occasions

This is especially important for "no TV on non-designated days" and "30 minutes every day this month". It also prevents confusion when traveling across timezones.

## 5. Support a few first-class goal patterns from day one

I would treat these as first-class patterns built from the same primitives:

- Habit completion: "did cardio today"
- Target value: "reach 100 lbs"
- Task completion: one-off task with optional checklist
- Allowance goal: "do not exceed X over last N days"
- Milestone sequence: a goal with ordered checkpoints
- Composite goal: score derived from multiple sub-goals

Composite goals are worth planning for early, even if not implemented immediately. They make dashboards more useful later, for example "Health score" from cardio, weight trend, sleep consistency, and training sessions.

## 6. Forecasting should be pluggable and explainable

Your old weight-loss project is the right precedent. I would formalize forecasts as:

- algorithm id
- applicable metric types
- required minimum history
- output series
- confidence or reliability score
- explanation string for the UI

Important refinement: the UI should be able to say why a forecast is weak, such as "insufficient recent history" or "high variance". Otherwise users tend to over-trust projected completion dates.

I would start with:

- simple linear trend
- rolling average delta
- weekday-weighted numeric forecast
- no-forecast mode when data is insufficient

## 7. Widgets should be configuration records, not ad hoc UI state

Since you want shareable rendered widgets, define widgets as saved server-backed objects:

- widget type
- target goal(s)
- date window
- display options
- render format support: app card, PNG, maybe JSON for future automation

That opens the door to:

- dashboard composition
- stable share links
- server-side image rendering
- future background refresh and caching

For the PNG sharing case, prefer a signed share token or public widget token over exposing raw internal ids.

## 8. Use tags, not just dashboards, for organization

Dashboards are useful, but tags are more flexible:

- one goal can appear in `health` and `daily-routine`
- dashboard widgets can filter by tags
- future reporting becomes easier

I would treat dashboards as layouts over widgets, and tags as the main organizational dimension on goals.

## 9. Reconsider custom schema version tracking

You mentioned a `dbversion` tracker in a configuration table. Since you already want Alembic, I would not use a separate custom schema-version mechanism unless there is a very specific reason.

Recommended split:

- Alembic owns schema versioning
- app config table stores application-level settings and feature flags
- seed/example-data versioning is tracked separately if needed

Duplicating schema version state in two places usually creates drift and confusion.

## 10. Reconsider fully stateless signed-cookie auth

A one-hour signed cookie can work, but pure stateless session cookies make revocation and audit harder.

I recommend one of these two designs:

- Preferred: signed session cookie pointing to a server-side session table with expiration, revocation, and last-seen tracking
- Simpler: stateless signed cookie plus a `session_version` on the user record so password changes and admin revocation can invalidate old cookies

If you expect only a few users and want straightforward admin controls, server-side sessions are the cleaner choice.

## 11. Plan for ownership and sharing boundaries early

Even if the first release is mostly single-user in practice, decide now whether the product is:

- single-tenant personal app with multiple login accounts mainly for admin/testing
- true multi-user app where each user owns separate goals/dashboards/widgets
- shared household/team app with optional cross-user visibility

This decision affects schema boundaries, permissions, share links, and dashboard design. It is cheaper to decide this early.

## 12. Add notes, attachments, and audit trail to entries

Manual updates become much more useful if each entry can optionally store:

- note text
- attached image or file reference
- source type: manual, import, system-derived
- edit history

For example, a weight entry with a note about illness or travel can explain a sudden trend change. Even if attachments ship later, the entry model should leave room for them now.

## 13. Make "example data" a seeded fixture system

The example-data account idea is good. I would refine it into a repeatable seed system:

- deterministic seed profiles, such as `basic`, `fitness`, `finance`
- can be applied in dev/test without hand-entering data
- can seed widgets and dashboards too, not just raw goals

This will help both development and screenshots for the public README.

## 14. Pick testing layers now

The testing requirement should be more explicit so the repo structure stays clean:

- API/unit tests: `pytest`, `httpx`, FastAPI test client
- DB migration tests: apply migrations in disposable DB and verify upgrade path
- Frontend unit/component tests: `vitest` and Vue Test Utils
- End-to-end smoke tests: Playwright against the compose stack once the app exists

That is enough structure to keep quality high without overdesigning the test matrix.

## 15. Define an MVP boundary before building dashboards and forecasts deeply

The feature set can expand fast. I would set MVP as:

1. authentication and user settings
2. create/edit/archive goals
3. record manual entries
4. view per-goal history and current status
5. support three goal patterns: habit, target value, task/checklist
6. basic dashboard with saved widgets

Then phase 2:

1. rolling-window allowance goals
2. forecast algorithms
3. PNG widget rendering and share links
4. admin registration codes
5. seed/example profiles

This keeps the early schema and UI decisions honest.

## 16. Add explicit non-goals for the first release

This helps prevent scope creep. I would explicitly defer things like:

- automatic imports from wearables or third-party services
- collaborative goals across users
- mobile app
- push notifications
- highly advanced forecasting
- arbitrary custom formula builder in the UI

Those can all come later if the foundation is right.

## Questions For Approval

These are the design decisions I would want approved before implementation starts:

1. Should the first release target a true multi-user product, or should we optimize for a single-user personal app with admin/auth mainly for safety and future growth?
2. Do you want goal storage built around generic primitives (`goal`, `metric`, `entry`, `rule`, `widget`) even if that makes the initial schema a little more abstract?
3. Should we use server-side sessions instead of a purely stateless signed cookie so admin revocation and password-change invalidation are straightforward?
4. Do you want Alembic to be the only schema version authority, with any config table used only for application settings rather than DB version tracking?
5. Is the MVP boundary above acceptable, with rolling-window logic, advanced forecasts, and PNG sharing treated as phase 2 instead of day-one requirements?
6. Should widgets and dashboards be private per user by default, with explicit share links only for the PNG/public-render use case?
7. Do you want seed/example data treated as a formal fixture system that can populate goals, entries, widgets, and dashboards for dev/test/demo use?

## Approval Outcomes

This section records the current approved direction from the first design review.

### Multi-user scope

Approved: support multiple users from the start.

Reasoning captured from review:

- demo/example accounts are important early
- real accounts are also needed early
- ownership and permissions should therefore be modeled from the beginning

### Schema abstraction level

Deferred for later approval.

Direction for now:

- keep exploring the design before locking schema details
- the final schema and detailed data model should be proposed explicitly in a later step for approval

### Session architecture

Decision leaning: choose the most maintainable option, not theoretical HA.

Constraints captured from review:

- low expected session state
- desire to preserve auth across container restarts during testing
- HA production deployment is not a primary goal

Current recommendation:

- prefer the simplest maintainable auth/session design that preserves login continuity across routine container restarts
- final auth design should be proposed in the next architecture step with the tradeoffs spelled out clearly

### Schema upgrades and seeded data evolution

Approved direction:

- Alembic should remain responsible for schema upgrades
- the system also needs a formal mechanism to evolve example/test/demo data when features are added

Implication:

- schema migration and seeded data migration should be treated as related but separate concerns
- example-data users flagged in the database should be able to receive new seeded feature data after upgrades

### Delivery phases

Approved direction:

- do not force everything into a single MVP bucket
- create a multi-phase delivery plan after the design is fleshed out further

### Share links

Approved direction:

- widget/dashboard share links should use UUID-style public identifiers
- links should have a configurable expiration, including no-expiration
- users should be able to create, view, revoke, and manage these links from profile/settings UI

### Example data system

Approved: example data should be a formal seeded system.

Required behavior:

- seed example/demo users on account creation when applicable
- add new seeded data to existing flagged example-data accounts when new features are introduced

## Next Approval Round

The next design pass should come back with explicit proposals for approval on:

1. the concrete schema and entity relationships
2. the session/auth design choice
3. the seeded data migration mechanism
4. the phased delivery plan
5. the share-link permission and lifecycle model
