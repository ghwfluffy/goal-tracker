# Frontend Unified CSS System

The frontend now uses a shared token-driven CSS system instead of treating each Vue component as its own visual island.

## Primary Sources Of Truth

### Global design tokens

The root token layer lives in [`web/src/style.css`](/home/tfuller/git/goals/web/src/style.css).

That file owns the stable visual primitives for the app:

- typography tokens like label and caption sizes
- spacing tokens such as `--space-4` and `--space-6`
- radius tokens such as `--radius-md`, `--radius-lg`, and `--radius-pill`
- text color tokens such as `--color-text-strong`, `--color-text-muted`, and `--color-text-faint`
- border, surface, and shadow tokens
- chart color tokens such as `--chart-series-primary`, `--chart-series-success`, and `--chart-grid-line`

If a style choice should be reusable across more than one feature, it should usually start here.

### Shared global utilities

[`web/src/style.css`](/home/tfuller/git/goals/web/src/style.css) also contains a few global utility classes for patterns that are intentionally reused across many views:

- `panel-card`
- `status-card`
- `surface-panel-soft`
- `empty-dashed-state`
- `shell-center`

These are for stable shell-level patterns, not one-off layout hacks.

### Shared home-management styles

Metrics and goals share management UI CSS in [`web/src/components/home/management.css`](/home/tfuller/git/goals/web/src/components/home/management.css).

That file owns the common patterns for:

- management shells
- table styling
- card styling
- shared section heading copy inside those views
- row/kebab alignment

If metrics and goals diverge visually, fix the shared file instead of patching one tab locally unless the difference is intentional and domain-specific.

### Shared management toolbar component

The metrics/goals toolbar now comes from [`web/src/components/home/ManagementToolbar.vue`](/home/tfuller/git/goals/web/src/components/home/ManagementToolbar.vue).

If a backend-managed entry screen needs the same toolbar pattern, reuse that component before inventing another toolbar.

### Chart theme bridge

Chart colors are sourced from CSS variables through [`web/src/lib/theme.ts`](/home/tfuller/git/goals/web/src/lib/theme.ts).

Charts should not hardcode palette values if the equivalent token already exists. If the visual language changes, update the CSS variables first so both CSS and charts move together.

## What Should Stay Local

Scoped component CSS is still appropriate for:

- layout that is truly specific to one component
- structural styles tied to one template
- domain-specific affordances like the goal exception-date chips
- sizing rules that are local to one dialog or one widget

Even in scoped CSS, prefer token references over raw literals for color, spacing, radius, borders, and shadows.

## Current Styling Boundaries

Use this rough decision order:

1. If the style is part of the app’s visual language, add or reuse a token in [`web/src/style.css`](/home/tfuller/git/goals/web/src/style.css).
2. If the pattern repeats across multiple screens, create or reuse a shared utility class or shared component stylesheet.
3. If the pattern is specific to one component’s structure, keep it scoped in that component.

The intent is not “everything must be global.” The intent is “stable visual decisions should have a stable home.”
