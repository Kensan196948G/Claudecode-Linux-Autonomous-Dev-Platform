# Cluster Architecture

## Roles
- Controller: scheduling, dispatch, dashboard, cluster state
- Standby Controller: inactive until leader state changes
- Worker: develop, repair, verify, report, maintenance

## Communication
- SSH / rsync / JSON files
- Heartbeat from workers
- Job files distributed from controller
- File-based leader state for lightweight controller failover

## Safety
- Worker drain if memory_free_mb is below the configured threshold
- Worker drain if cpu_percent is above the configured threshold
- Worker drain if disk_used_percent is above the configured threshold
- WorkTree mandatory for code-changing jobs
- max_jobs=1 by default
- Failed jobs are requeued up to the retry limit and then archived
