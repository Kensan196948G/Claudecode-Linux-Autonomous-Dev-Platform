# Cluster Failover Policy

## Leader
- `cluster/leader/elect_leader.py` creates or reads `cluster/leader/leader.json`.
- Only the leader runs `cluster_orchestrator.sh`.
- Set `CLUSTER_CONTROLLER_ID` on each controller node.

## Failover
- `cluster/leader/failover.py` switches to the next enabled controller.
- The file-based leader is intentionally simple and inspectable.
- Use shared storage or synced leader state before running multiple physical controllers.

## Failed Jobs
- Workers copy failed jobs into `cluster/failures`.
- `requeue_failed_jobs.py` requeues jobs until `CLUSTER_JOB_RETRY_LIMIT`.
- Jobs that exceed retry limit move to `cluster/archive` as `permanent_fail`.
