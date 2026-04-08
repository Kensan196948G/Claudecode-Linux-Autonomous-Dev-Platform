#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/ci/common.sh"

require_cmd gh
require_cmd python3

REPO_PATH="$(ci_repo_path)"
ensure_repo "$REPO_PATH"
cd "$REPO_PATH"

RUN_JSON="$DEVOS_HOME/runtime/ci/latest_run.json"
ci_log "check status repo=$REPO_PATH"

gh run list --limit 1 --json databaseId,status,conclusion,workflowName,headBranch,displayTitle,createdAt > "$RUN_JSON"

python3 - "$DEVOS_STATE_FILE" "$RUN_JSON" "$DEVOS_LOCK_DIR/state.lock" "$REPO_PATH" <<'PY'
import fcntl
import json
import sys
from datetime import datetime
from pathlib import Path

state_path = Path(sys.argv[1])
run_path = Path(sys.argv[2])
lock_path = Path(sys.argv[3])
repo_path = sys.argv[4]
runs = json.loads(run_path.read_text(encoding="utf-8"))

lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("w", encoding="utf-8") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    ci = state.setdefault("ci", {})
    ci["repo_path"] = repo_path
    ci["last_checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if runs:
        run = runs[0]
        conclusion = run.get("conclusion")
        status = run.get("status")
        workflow = run.get("workflowName")
        title = run.get("displayTitle")
        ci["last_run_status"] = conclusion if conclusion else status
        ci["last_run_id"] = run.get("databaseId")
        ci["last_failure_summary"] = f"{workflow}: {title}" if conclusion == "failure" else None
    else:
        ci["last_run_status"] = "none"
        ci["last_run_id"] = None
        ci["last_failure_summary"] = None
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
