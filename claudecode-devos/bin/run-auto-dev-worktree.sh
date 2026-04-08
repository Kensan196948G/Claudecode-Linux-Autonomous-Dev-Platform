#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

SELECTED="$DEVOS_HOME/runtime/projects/selected_project.json"
LOG_FILE="$DEVOS_HOME/runtime/agent_logs/development.log"
PROMPT="$DEVOS_HOME/runtime/prompts/current_prompt.md"
mkdir -p "$(dirname "$LOG_FILE")"

PROJECT_REPO="$(python3 - "$SELECTED" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("repository", ""))
PY
)"
PROJECT_ID="$(python3 - "$SELECTED" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("id", "project"))
PY
)"
ISSUE_NO="$("$DEVOS_HOME/ops/state_manager.py" get github.current_issue | tr -d '"')"
if [[ -z "$ISSUE_NO" || "$ISSUE_NO" == "null" ]]; then
  ISSUE_NO="adhoc"
fi

if [[ -z "$PROJECT_REPO" || ! -d "$PROJECT_REPO/.git" ]]; then
  printf '%s [DEV-WT] invalid repo=%s\n' "$(date '+%F %T')" "$PROJECT_REPO" >> "$LOG_FILE"
  exit 0
fi

SAFE_PROJECT="$(printf '%s' "$PROJECT_ID" | tr -cd '[:alnum:]_.-')"
SAFE_ISSUE="$(printf '%s' "$ISSUE_NO" | tr -cd '[:alnum:]_.-')"
BRANCH="feature/${SAFE_PROJECT}-issue-${SAFE_ISSUE}-$(date +%H%M%S)"
WT_PATH="$("$DEVOS_HOME/ops/worktree_manager.sh" create "$PROJECT_REPO" "$BRANCH" "feature")"

"$DEVOS_HOME/ai/agent_phase_logger.sh" "DEVELOP" "feature worktree created $WT_PATH"
printf '%s [DEV-WT] start wt=%s branch=%s\n' "$(date '+%F %T')" "$WT_PATH" "$BRANCH" >> "$LOG_FILE"

if [[ ! -s "$PROMPT" ]]; then
  "$DEVOS_HOME/ai/prompt_builder.py" >/dev/null
fi

cd "$WT_PATH"
timeout "$AUTO_DEV_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" < "$PROMPT" >> "$LOG_FILE" 2>&1 || true

PR_URL=""
if [[ -n "$(git status --porcelain)" ]]; then
  git add .
  git commit -m "feat: automated development in worktree" >> "$LOG_FILE" 2>&1 || true
  git push -u origin "$BRANCH" >> "$LOG_FILE" 2>&1 || true
  PR_URL="$(gh pr create --title "feat: automated development for ${PROJECT_ID}" --body "Automated change created in isolated worktree" --base "$GITHUB_BASE_BRANCH" --head "$BRANCH" 2>> "$LOG_FILE" || true)"
fi

python3 - "$DEVOS_STATE_FILE" "$DEVOS_LOCK_DIR/state.lock" "$PROJECT_ID" "$BRANCH" "$WT_PATH" "$PR_URL" <<'PY'
import fcntl
import json
import sys
from datetime import datetime
from pathlib import Path

state_path = Path(sys.argv[1])
lock_path = Path(sys.argv[2])
project_id, branch, wt_path, pr_url = sys.argv[3:7]
with lock_path.open("w", encoding="utf-8") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    history = state.setdefault("history", {}).setdefault("last_project_runs", [])
    history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project": project_id,
        "branch": branch,
        "path": wt_path,
        "pr": pr_url or None,
        "type": "develop",
    })
    state["history"]["last_project_runs"] = history[-30:]
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cd "$PROJECT_REPO"
"$DEVOS_HOME/ops/worktree_manager.sh" remove "$PROJECT_REPO" "$BRANCH" "feature" >/dev/null || true
"$DEVOS_HOME/ai/agent_phase_logger.sh" "DEVELOP" "feature worktree removed $WT_PATH"
printf '%s [DEV-WT] end branch=%s pr=%s\n' "$(date '+%F %T')" "$BRANCH" "$PR_URL" >> "$LOG_FILE"
