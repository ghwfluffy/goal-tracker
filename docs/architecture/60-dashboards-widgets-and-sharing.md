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

Current implemented slice:

- user-owned saved dashboards
- one default dashboard per user
- separate dashboard edit mode for adding and updating widgets
- metric-history, metric-summary, goal-progress, goal-summary, goal-calendar, and goal-checklist widgets
- date-metric `days since` summary widgets for streak-style dashboards
- goal-progress series derived from metric history rather than stored separately
- goal-calendar widgets can aggregate one goal, an explicit goal set, or all active goals across goal-length, current-month, and rolling-four-week views
- checklist widgets can render ordered goal subtasks as checkboxes and write completions back to the goal
- user-managed share links for dashboards and widgets
- read-only public dashboard pages
- server-rendered widget preview PNGs for Discord, Teams, and other OG/Twitter consumers

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
- goal-calendar widgets may either target an explicit ordered goal set or all active goals for the user

## Metric-History Widgets

The system should support widgets whose primary subject is a metric rather than a goal.

Examples:

- raw `weight` history graph
- rolling average of `weight`
- `cardio_minutes` history over the last 90 days
- summary card for latest metric value and trend
- summary card for `days since last drink`, `days since injury`, or similar date metrics
- performance-attempt chart such as 2km row times across all attempts

This is useful because metrics can persist longer than any one goal and may remain valuable to view between goal cycles.

Current time semantics:

- metric entry timestamps are stored in UTC
- frontend timestamp display should use the browser timezone
- goal and day-boundary interpretation should use the saved user profile timezone

## Public Sharing

Sharing is an explicit, user-managed feature.

Current implemented direction:

- share links use random token-based public identifiers
- each link targets either one widget or one dashboard
- links default to a 30-day expiration and can instead be created with no expiration
- links can be revoked independently without deleting the widget or dashboard
- copied links append an ignored `?t=` timestamp query purely to force fresh preview fetches

## Share-Link Management

Users should be able to manage share links from profile/settings UI.

Current implemented capabilities:

- create a link
- choose the default 30-day expiration or unlimited expiration
- view active, expired, and revoked links
- revoke a link
- inspect target and creation details
- quick-copy a fresh cache-busted URL

## Rendering Direction

Current implemented direction:

- public share pages are server-rendered so preview crawlers do not depend on client-side JavaScript
- shared widget pages render the actual widget graph inline from the saved series rather than showing only the OG preview image
- widgets have a simplified server-side PNG renderer focused on the main value and uncluttered trend context
- dashboards render as read-only public HTML rather than editable app chrome
- avoid exposing internal database identifiers in public URLs
- support widgets that can explain why a scheduled day is excluded, such as exception dates rendered as `skipped`

## Privacy Model

Defaults:

- dashboards and widgets are private by default
- public access exists only through explicit share links
- share-link access should be auditable where practical

## Open Design Item

Share-link access auditing is still only partially addressed. Public access works through explicit tokens, but detailed access-event capture is still a later improvement.
