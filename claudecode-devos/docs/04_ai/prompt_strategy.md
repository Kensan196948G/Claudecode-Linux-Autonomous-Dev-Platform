# Prompt Strategy

## Inputs
- `state.json` for current state and decision mode.
- Selected GitHub Issue for task context.
- CI failure summary for repair context.
- DevOS Docs for operating policy.

## Principles
- Prefer the smallest safe change.
- Keep memory usage low under pressure.
- Prioritize CI repair when the decision mode is `repair_ci`.
- Update Docs when behavior, operations, or policy changes.
- Never push directly to the base branch.
