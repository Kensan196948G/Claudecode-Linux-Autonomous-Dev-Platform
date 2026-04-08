#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

WORKER_ID="$(python3 - "$CLUSTER_WORKER_CONFIG" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data["worker"]["id"])
PY
)"

for job in "$DEVOS_HOME"/cluster/jobs/job-*.json; do
  [[ -f "$job" ]] || continue

  readarray -t JOB_STATE < <(python3 - "$job" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("assigned_worker", ""))
print(data.get("status", ""))
PY
)

  if [[ "${JOB_STATE[0]}" == "$WORKER_ID" && "${JOB_STATE[1]}" == "assigned" ]]; then
    "$DEVOS_HOME/cluster/workers/run_job.sh" "$job"
  fi
done
