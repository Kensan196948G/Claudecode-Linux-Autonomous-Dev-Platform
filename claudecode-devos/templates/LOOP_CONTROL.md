# LOOP_CONTROL

## Loop Commands

```text
/loop 30m ClaudeOS Monitor
/loop 2h ClaudeOS Development
/loop 1h ClaudeOS Verify
/loop 1h ClaudeOS Improvement
```

## Conditions
- 3 consecutive successful cycles means stable.
- Stable state may create PRs.
- Merge only when CI is green and merge policy allows it.
- On error, switch to repair mode.
- Stop automated repair when retry limits are reached.
- Never push directly to the base branch.
