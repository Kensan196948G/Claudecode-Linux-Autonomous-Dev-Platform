#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG="$DEVOS_LOG_DIR/cluster-orchestrator.log"
mkdir -p "$DEVOS_LOG_DIR"

LEADER="$("$DEVOS_HOME/cluster/leader/elect_leader.py")"
if [[ "$CLUSTER_CONTROLLER_ID" != "$LEADER" ]]; then
  echo "$(date '+%F %T') [CLUSTER] not leader current=$CLUSTER_CONTROLLER_ID leader=$LEADER exit" >> "$LOG"
  exit 0
fi

echo "$(date '+%F %T') [CLUSTER] cycle start" >> "$LOG"

"$DEVOS_HOME/cluster/controller/sync_cluster.sh" >> "$LOG" 2>&1 || true
"$DEVOS_HOME/cluster/controller/ingest_heartbeats.py" >> "$LOG" 2>&1 || true
"$DEVOS_HOME/cluster/controller/requeue_failed_jobs.py" >> "$LOG" 2>&1 || true
"$DEVOS_HOME/cluster/controller/dispatch_jobs.py" >> "$LOG" 2>&1 || true
"$DEVOS_HOME/cluster/controller/sync_cluster.sh" >> "$LOG" 2>&1 || true

echo "$(date '+%F %T') [CLUSTER] cycle end" >> "$LOG"
