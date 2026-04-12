# How To Document Style Changes

Use this directory to record style changes that future agents should know about.

## Document A Style Change When

Create or update a doc in `docs/style` if the change establishes a rule like:

- prefer a shared component instead of repeating the same structure
- prefer a shared stylesheet or token layer instead of duplicating literals
- keep page-level views thin and composition-oriented
- route a class of user feedback through one consistent UI pattern
- treat a certain form of duplication as unacceptable going forward

## Document Shape

Keep style docs short and operational.

A useful doc usually answers:

1. what the rule is
2. why the rule exists
3. where the shared implementation lives
4. how future agents should extend it safely

## Prefer Updating Over Sprawling

If a new correction fits an existing topic, update that document instead of creating another tiny file.

Examples:

- update the frontend CSS docs when the token system changes
- update the repository coding-style doc when a broader composition rule is introduced

## Current Topic Split

Today the directory is split into:

- repo-wide coding-style guidance
- frontend unified CSS guidance

If another stable style topic emerges, add it as a focused doc rather than dumping everything into one giant file.
