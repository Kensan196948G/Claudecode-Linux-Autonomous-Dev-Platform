# Cluster Policy

1. Controller does not perform direct code editing.
2. Workers must use isolated worktrees.
3. Repair jobs should prefer dedicated repair-tagged workers.
4. Drain nodes must not receive new jobs.
5. Failed jobs must be logged and reviewed in the dashboard.
6. `CLUSTER_SYNC_ENABLED=false` is the safe default for local testing.
7. Only the elected leader may run the cluster orchestrator.
8. Failed jobs may be retried up to `CLUSTER_JOB_RETRY_LIMIT`.
