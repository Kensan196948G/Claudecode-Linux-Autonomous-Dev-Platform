# Log Policy

## Retention
- Active logs are retained for 7 days by default.
- Older logs are compressed into `runtime/archive/logs`.
- Compressed archives are deleted after 30 days by default.

## Controls
- `LOG_RETENTION_DAYS`
- `ARCHIVE_RETENTION_DAYS`
- `DEVOS_LOG_ARCHIVE_DIR`

## Job
- Script: `ops/log_retention.sh`
- Timer: `log-retention.timer`

## Notes
Long-running autonomous systems must treat logs as bounded data. Disk pressure can force `decision.next_action=suspend`.
