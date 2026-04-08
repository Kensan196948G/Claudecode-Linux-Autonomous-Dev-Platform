#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

SELECTED="$DEVOS_HOME/runtime/projects/selected_project.json"
LOG_FILE="$DEVOS_LOG_DIR/project-runner.log"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_HOME/runtime/projects"

"$DEVOS_HOME/ops/project_scheduler.py" >/dev/null

if [[ ! -s "$SELECTED" ]]; then
  printf '%s [RUNNER] no selected project file\n' "$(date '+%F %T')" >> "$LOG_FILE"
  exit 0
fi

PROJECT_ID="$(python3 - "$SELECTED" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("id", ""))
PY
)"
PROJECT_REPO="$(python3 - "$SELECTED" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("repository", ""))
PY
)"

if [[ -z "$PROJECT_ID" || -z "$PROJECT_REPO" ]]; then
  printf '%s [RUNNER] no project selected\n' "$(date '+%F %T')" >> "$LOG_FILE"
  exit 0
fi

printf '%s [RUNNER] selected=%s\n' "$(date '+%F %T')" "$PROJECT_ID" >> "$LOG_FILE"

if [[ ! -d "$PROJECT_REPO" ]]; then
  printf '%s [RUNNER] repository not found project=%s repo=%s\n' "$(date '+%F %T')" "$PROJECT_ID" "$PROJECT_REPO" >> "$LOG_FILE"
  "$DEVOS_HOME/ops/state_manager.py" set system.last_error "repository not found: $PROJECT_REPO"
  exit 0
fi

if ! USAGE_CHECK_OUTPUT="$("$DEVOS_HOME/ops/usage_manager.py" check 2>&1)"; then
  printf '%s [RUNNER] skipped project=%s reason=%s\n' "$(date '+%F %T')" "$PROJECT_ID" "$USAGE_CHECK_OUTPUT" >> "$LOG_FILE"
  exit 0
fi
printf '%s [RUNNER] usage check: %s\n' "$(date '+%F %T')" "$USAGE_CHECK_OUTPUT" >> "$LOG_FILE"

"$DEVOS_HOME/ops/state_manager.py" set projects.active_project "$PROJECT_ID"
"$DEVOS_HOME/ops/state_manager.py" touch projects.last_project_switch
"$DEVOS_HOME/ops/state_manager.py" set ci.repo_path "$PROJECT_REPO"
"$DEVOS_HOME/ops/state_manager.py" set github.repo "$PROJECT_REPO"

"$DEVOS_HOME/ai/issue_prioritizer.py" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ai/prompt_builder.py" >> "$LOG_FILE" 2>&1 || true

START_TIME="$(date +%s)"
WORKTREE_ENABLED_STATE="$("$DEVOS_HOME/ops/state_manager.py" get worktree.enabled | tr -d '"')"
if [[ "$WORKTREE_ENABLED" == "true" && "$WORKTREE_ENABLED_STATE" != "false" && -d "$PROJECT_REPO/.git" ]]; then
  if [[ "${DEVOS_CLAUDE_FOREGROUND:-false}" == "true" ]]; then
    "$DEVOS_HOME/bin/run-auto-dev-worktree.sh" || true
  else
    "$DEVOS_HOME/bin/run-auto-dev-worktree.sh" >> "$LOG_FILE" 2>&1 || true
  fi
else
  if [[ "${DEVOS_CLAUDE_FOREGROUND:-false}" == "true" ]]; then
    AUTO_DEV_REPO="$PROJECT_REPO" "$DEVOS_HOME/bin/run-auto-dev.sh" || true
  else
    AUTO_DEV_REPO="$PROJECT_REPO" "$DEVOS_HOME/bin/run-auto-dev.sh" >> "$LOG_FILE" 2>&1 || true
  fi
fi
END_TIME="$(date +%s)"
DURATION="$((END_TIME - START_TIME))"
"$DEVOS_HOME/ops/usage_manager.py" record "$DURATION" >> "$LOG_FILE" 2>&1 || true

python3 - "$DEVOS_PROJECTS_FILE" "$SELECTED" <<'PY'
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

projects_path = Path(sys.argv[1])
selected_path = Path(sys.argv[2])
projects = json.loads(projects_path.read_text(encoding="utf-8"))
selected = json.loads(selected_path.read_text(encoding="utf-8"))
selected_id = selected.get("id")
finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for project in projects.get("projects", []):
    if project.get("id") == selected_id:
        project["last_run_at"] = finished_at
        project["last_result"] = "completed"
        selected["last_run_at"] = finished_at
        selected["last_result"] = "completed"

with NamedTemporaryFile("w", encoding="utf-8", dir=projects_path.parent, delete=False) as tmp:
    json.dump(projects, tmp, ensure_ascii=False, indent=2)
    tmp.write("\n")
    tmp_name = tmp.name
os.replace(tmp_name, projects_path)

with NamedTemporaryFile("w", encoding="utf-8", dir=selected_path.parent, delete=False) as tmp:
    json.dump(selected, tmp, ensure_ascii=False, indent=2)
    tmp.write("\n")
    tmp_name = tmp.name
os.replace(tmp_name, selected_path)
PY

printf '%s [RUNNER] completed=%s\n' "$(date '+%F %T')" "$PROJECT_ID" >> "$LOG_FILE"
