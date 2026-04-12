# How To Extend Frontend Unified CSS

Future agents should use this order when adding frontend styles.

## Extension Rules

1. Look for an existing token in [`web/src/style.css`](/home/tfuller/git/goals/web/src/style.css) before adding any new color, spacing, radius, border, or shadow literal.
2. If the same pattern appears in more than one component, extract it into a shared class, shared stylesheet, or shared Vue component instead of duplicating scoped CSS.
3. If the change affects metrics/goals management screens, check [`web/src/components/home/management.css`](/home/tfuller/git/goals/web/src/components/home/management.css) and [`web/src/components/home/ManagementToolbar.vue`](/home/tfuller/git/goals/web/src/components/home/ManagementToolbar.vue) first.
4. If the change affects chart styling, update the CSS token layer and [`web/src/lib/theme.ts`](/home/tfuller/git/goals/web/src/lib/theme.ts) instead of hardcoding ECharts colors in-place.
5. Keep scoped CSS for component-specific structure, but use token references inside that scoped CSS whenever possible.

## When To Add A New Token

Add a new root CSS variable when the style represents one of these:

- a shared semantic color
- a reusable surface/background treatment
- a repeated border treatment
- a repeated shadow treatment
- a spacing or radius value that is showing up more than once
- a chart color that should track the main app theme

Do not add a new token for a one-off arbitrary number unless it is clearly becoming part of the design language.

## When To Extract Shared CSS

Extract shared CSS when:

- two or more components use the same table/card/list/shell treatment
- the same heading/copy/form pattern keeps being redefined
- one feature screen starts drifting from another equivalent screen because of copy-pasted scoped CSS

If a pattern is reused with behavior and markup, prefer a shared Vue component. If it is reused as styling only, prefer a shared stylesheet or utility class.

## Anti-Patterns

Avoid these unless there is a strong local reason:

- adding new raw hex or `rgba(...)` values directly in component CSS for common UI colors
- copying a toolbar, table, card shell, or dialog pattern into a second component
- hardcoding chart palette values in chart option builders
- adding a second “almost the same” surface style instead of extending the shared token set

## Review Checklist

Before finishing a frontend styling change, check:

1. Did I reuse an existing token instead of introducing a new literal?
2. Did I move repeated styles to a shared location if more than one component needs them?
3. Does this change preserve consistency with existing management screens and shell panels?
4. If charts are affected, do their colors still come from the shared chart theme bridge?
5. Did I run [`./scripts/validate.sh`](/home/tfuller/git/goals/scripts/validate.sh)?
