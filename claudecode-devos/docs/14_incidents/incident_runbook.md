# Incident Runbook

## Claude Freeze
1. Check `runtime/pids/claude.pid`.
2. Check `runtime/logs/claude-safe.log`.
3. Run recovery if needed: `ops/recovery.sh`.
4. Inspect `system.last_error` in `config/state.json`.

## CI Infinite Failure
1. Check `ci.repair_attempt_count`.
2. Confirm `ci.repair_attempt_limit`.
3. If limit reached, set `decision.next_action=suspend`.
4. Review `runtime/ci/last_failure_summary.txt`.

## GitHub Integration Failure
1. Run `gh auth status`.
2. Check token scopes and repository access.
3. Inspect `github.last_error` in `state.json`.

## Cluster Dispatch Failure
1. Check `cluster/leader/leader.json`.
2. Check `cluster/controller/cluster_state.json`.
3. Check `cluster/failures` and `cluster/archive`.
4. Confirm `CLUSTER_SYNC_ENABLED` before debugging SSH/rsync.

## Disk Pressure
1. Run `ops/log_retention.sh`.
2. Check `runtime/logs`.
3. Check `runtime/worktrees`.
4. Confirm old archives are being deleted.
