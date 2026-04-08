#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

if [[ "$CLUSTER_SYNC_ENABLED" != "true" ]]; then
  exit 0
fi

WORKERS_JSON="$CLUSTER_STATE_FILE"
readarray -t WORKERS < <(python3 - "$WORKERS_JSON" <<'PY'
import json
import sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for worker in state.get("workers", []):
    if worker.get("enabled") and worker.get("ip"):
        print(f"{worker.get('id')} {worker.get('ip')}")
PY
)

for worker in "${WORKERS[@]}"; do
  read -r _worker_id host <<< "$worker"
  rsync -az "$DEVOS_HOME/cluster/jobs/" "$CLUSTER_DEFAULT_USER@${host}:$DEVOS_HOME/cluster/jobs/" || true
  rsync -az "$CLUSTER_DEFAULT_USER@${host}:$DEVOS_HOME/cluster/events/" "$DEVOS_HOME/cluster/events/" || true
done
