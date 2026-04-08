# Decision Policy

## next_action
- `develop`: run the normal development session.
- `repair_ci`: repair the latest failing CI run.
- `cooldown`: wait for resource pressure to recover.
- `suspend`: stop autonomous execution and wait for human review.
- `idle`: do nothing.

## suspend conditions
- Disk usage is above the configured alert threshold.
- CI repair attempts reached `repair_attempt_limit`.
- State is unreadable or required repository context is missing.

## merge policy
- Merge only when CI is green enough for GitHub to report `mergeStateStatus=CLEAN`.
- Review state must be `APPROVED`, empty, or unavailable.
- Auto merge must be explicitly enabled.
