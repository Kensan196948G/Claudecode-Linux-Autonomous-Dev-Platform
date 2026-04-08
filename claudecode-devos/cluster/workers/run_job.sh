#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

JOB_FILE="${1:-}"
LOG="$DEVOS_LOG_DIR/cluster-worker.log"
FAILURE_DIR="$DEVOS_HOME/cluster/failures"

[[ -f "$JOB_FILE" ]] || exit 1
mkdir -p "$DEVOS_LOG_DIR"

readarray -t JOB_INFO < <(python3 - "$JOB_FILE" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data["job_id"])
print(data["type"])
print(data.get("project_id", ""))
print(data.get("repo_path", ""))
print(data.get("issue_number", ""))
PY
)

JOB_ID="${JOB_INFO[0]}"
JOB_TYPE="${JOB_INFO[1]}"
PROJECT_ID="${JOB_INFO[2]}"
REPO_PATH="${JOB_INFO[3]}"
ISSUE_NUMBER="${JOB_INFO[4]}"

echo "$(date '+%F %T') [WORKER] start job=$JOB_ID type=$JOB_TYPE" >> "$LOG"

python3 - "$JOB_FILE" "$DEVOS_STATE_FILE" "$DEVOS_PROJECTS_FILE" "$DEVOS_HOME/runtime/projects/selected_project.json" "$PROJECT_ID" "$REPO_PATH" "$ISSUE_NUMBER" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime

job_file = Path(sys.argv[1])
state_file = Path(sys.argv[2])
projects_file = Path(sys.argv[3])
selected_file = Path(sys.argv[4])
project_id = sys.argv[5]
repo_path = sys.argv[6]
issue_number = sys.argv[7]

job = json.loads(job_file.read_text(encoding="utf-8"))
job["status"] = "running"
job["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

state = json.loads(state_file.read_text(encoding="utf-8"))
state.setdefault("github", {})["current_issue"] = None if not issue_number else issue_number
state.setdefault("ci", {})["repo_path"] = repo_path or state.get("ci", {}).get("repo_path")
state.setdefault("projects", {})["active_project"] = project_id or state.get("projects", {}).get("active_project")
state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if project_id and projects_file.exists():
    projects = json.loads(projects_file.read_text(encoding="utf-8")).get("projects", [])
    for project in projects:
        if project.get("id") == project_id:
            selected_file.parent.mkdir(parents=True, exist_ok=True)
            selected_file.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            break
PY

RESULT="completed"
case "$JOB_TYPE" in
  develop)
    "$DEVOS_HOME/bin/run-auto-dev-worktree.sh" || RESULT="failed"
    ;;
  repair_ci)
    "$DEVOS_HOME/ci/fetch_ci_failure.sh" || true
    "$DEVOS_HOME/ci/repair_ci_worktree.sh" || RESULT="failed"
    ;;
  verify)
    "$DEVOS_HOME/bin/run-session.sh" || RESULT="failed"
    ;;
  report)
    "$DEVOS_HOME/reports/report_generator.py" || RESULT="failed"
    ;;
  maintenance)
    "$DEVOS_HOME/ops/memory_guard.py" || RESULT="failed"
    ;;
  *)
    echo "$(date '+%F %T') [WORKER] unknown job type=$JOB_TYPE" >> "$LOG"
    RESULT="failed"
    ;;
esac

python3 - "$JOB_FILE" "$RESULT" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime
p = Path(sys.argv[1])
result = sys.argv[2]
data = json.loads(p.read_text(encoding="utf-8"))
data["status"] = result
data["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

if [[ "$RESULT" == "failed" ]]; then
  python3 - "$JOB_FILE" "$FAILURE_DIR" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime
job_file = Path(sys.argv[1])
failure_dir = Path(sys.argv[2])
data = json.loads(job_file.read_text(encoding="utf-8"))
data["status"] = "failed"
data["failed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
failure_dir.mkdir(parents=True, exist_ok=True)
(failure_dir / job_file.name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
fi

echo "$(date '+%F %T') [WORKER] end job=$JOB_ID type=$JOB_TYPE result=$RESULT" >> "$LOG"
