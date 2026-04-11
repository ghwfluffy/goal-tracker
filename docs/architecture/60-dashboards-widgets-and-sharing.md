# Dashboards, Widgets, And Sharing

## Dashboards

Dashboards are user-owned layouts composed of saved widgets.

Expected uses:

- category-specific views such as health, work, finances, or personal development
- daily summary screens
- focused progress pages for one area of life
- quick mobile-friendly check-in views for entering updates away from a desktop

## Widgets

Widgets should be stored as configuration records rather than temporary UI state.

Expected widget dimensions:

- widget type
- target goal, target goals, target metric, target metrics, or a mixed configuration
- date range or rolling window
- display options
- render mode such as app card or shareable PNG

This makes widgets reusable across dashboards and easier to render consistently.

Important design direction:

- widgets must support metric-history views that are not tied to an active goal
- a user should be able to keep a long-running metric widget, such as `weight` history, across multiple goal phases
- widgets should be able to distinguish `done`, `missed`, `skipped`, and `unknown` when the underlying goal pattern is schedule-based
- dashboards and widgets should remain usable on phone-sized screens, even when the desktop layout is richer

## Organization Model

The system should use both dashboards and tags.

Current direction:

- tags organize goals flexibly
- dashboards arrange widgets visually
- widgets can filter by explicit goal selection, metric selection, and later by tags when useful

## Metric-History Widgets

The system should support widgets whose primary subject is a metric rather than a goal.

Examples:

- raw `weight` history graph
- rolling average of `weight`
- `cardio_minutes` history over the last 90 days
- summary card for latest metric value and trend
- performance-attempt chart such as 2km row times across all attempts

This is useful because metrics can persist longer than any one goal and may remain valuable to view between goal cycles.

## Public Sharing

Sharing is an explicit, user-managed feature.

Current planned design:

- share links use UUID-style public identifiers
- each link targets a widget or dashboard
- each link may expire at a chosen time or never expire
- links can be revoked independently without deleting the widget or dashboard

## Share-Link Management

Users should be able to manage share links from profile/settings UI.

Expected capabilities:

- create a link
- choose expiration
- view active links
- revoke a link
- inspect target and creation details

## Rendering Direction

The product should eventually support image-style sharing for widgets.

Current direction:

- render widgets in-app first
- support server-side PNG rendering in a later phase
- avoid exposing internal database identifiers in public URLs
- support widgets that can explain why a scheduled day is excluded, such as exception dates rendered as `skipped`

## Privacy Model

Defaults:

- dashboards and widgets are private by default
- public access exists only through explicit share links
- share-link access should be auditable where practical

## Open Design Item

The detailed rules for whether full dashboards should be shareable in the same way as individual widgets still need final approval when the schema and permissions model are proposed.
