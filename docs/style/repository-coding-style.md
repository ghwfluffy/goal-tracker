# Repository Coding Style

This directory is not only for frontend visual styling.

`docs/style` is the home for coding-style guidance that future agents should follow when extending the repo. That includes:

- frontend CSS conventions
- component composition boundaries
- duplication-reduction rules
- naming and reuse conventions
- other style corrections that are broader than one isolated implementation detail

## When Something Belongs Here

Add or update a doc in `docs/style` when:

- a repeated code-style correction should affect future work
- a new shared convention is introduced and agents should reuse it
- the user explicitly sets a stylistic boundary for future changes
- a local refactor establishes a reusable pattern that should now be the default

Examples:

- “do not let view files turn into giant orchestrators; extract reusable components”
- “management screens should use shared toolbar/table/card patterns”
- “toasts should replace embedded success/error UI messages”
- “stable visual decisions should come from root CSS variables”

## What Does Not Belong Here

Do not use `docs/style` for:

- one-off implementation notes that are obvious from code
- product architecture decisions that belong in [`docs/architecture`](../architecture/README.md)
- temporary debugging notes
- customer-facing feature descriptions that belong in [`README.md`](../../README.md)

## How Future Agents Should Use This Directory

Before making a broad refactor or introducing a new reusable pattern:

1. read [`README.md`](./README.md)
2. check whether an existing doc already covers the convention
3. extend the existing doc instead of creating overlapping style guidance when possible

When a user corrects an agent on code organization or repo-wide style, that correction should usually be captured here.
