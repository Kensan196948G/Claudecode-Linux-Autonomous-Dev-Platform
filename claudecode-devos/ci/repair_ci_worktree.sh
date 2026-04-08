#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/ci/common.sh"

require_cmd git
require_cmd gh
require_cmd python3

REPO_PATH="$(ci_repo_path)"
BASE_BRANCH="$(ci_default_branch)"
ensure_repo "$REPO_PATH"

BRANCH="repair/ci-$(date +%Y%m%d-%H%M%S)"
WT_PATH="$("$DEVOS_HOME/ops/worktree_manager.sh" create "$REPO_PATH" "$BRANCH" "repair")"
PROMPT_FILE="$("$DEVOS_HOME/ci/build_repair_prompt.py")"
LOG_FILE="$DEVOS_LOG_DIR/repair-ci.log"

"$DEVOS_HOME/ai/agent_phase_logger.sh" "REPAIR" "CI repair worktree created $WT_PATH"
printf '%s [REPAIR-WT] start wt=%s branch=%s\n' "$(date '+%F %T')" "$WT_PATH" "$BRANCH" >> "$LOG_FILE"

cd "$WT_PATH"
timeout "$CI_REPAIR_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" < "$PROMPT_FILE" >> "$LOG_FILE" 2>&1 || true

if command -v pytest >/dev/null 2>&1; then
  pytest -q >> "$LOG_FILE" 2>&1 || true
fi

PR_URL=""
if [[ -n "$(git status --porcelain)" ]]; then
  git add .
  git commit -m "fix(ci): automated repair in worktree" >> "$LOG_FILE" 2>&1 || true
  git push -u origin "$BRANCH" >> "$LOG_FILE" 2>&1 || true
  PR_URL="$(gh pr create --title "fix(ci): automated repair attempt" --body "Automated CI repair generated in isolated worktree" --base "$BASE_BRANCH" --head "$BRANCH" 2>> "$LOG_FILE" || true)"
else
  ci_log "repair worktree produced no changes branch=$BRANCH"
fi

python3 - "$DEVOS_STATE_FILE" "$DEVOS_LOCK_DIR/state.lock" "$BRANCH" "$WT_PATH" "$PR_URL" <<'PY'
import fcntl
import json
import sys
from datetime import datetime
from pathlib import Path

state_path = Path(sys.argv[1])
lock_path = Path(sys.argv[2])
branch, wt_path, pr_url = sys.argv[3:6]
with lock_path.open("w", encoding="utf-8") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    ci = state.setdefault("ci", {})
    ci["repair_attempt_count"] = int(ci.get("repair_attempt_count") or 0) + 1
    ci["last_repair_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ci["last_repair_branch"] = branch
    if pr_url:
        ci["last_repair_pr"] = pr_url

    history = state.setdefault("history", {}).setdefault("last_ci_repairs", [])
    history.append({
        "time": ci["last_repair_at"],
        "branch": branch,
        "path": wt_path,
        "pr": pr_url or None,
        "type": "repair_ci",
    })
    state["history"]["last_ci_repairs"] = history[-20:]
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cd "$REPO_PATH"
"$DEVOS_HOME/ops/worktree_manager.sh" remove "$REPO_PATH" "$BRANCH" "repair" >/dev/null || true
"$DEVOS_HOME/ai/agent_phase_logger.sh" "REPAIR" "CI repair worktree removed $WT_PATH"
printf '%s [REPAIR-WT] end branch=%s pr=%s\n' "$(date '+%F %T')" "$BRANCH" "$PR_URL" >> "$LOG_FILE"
printf '%s\n' "$PR_URL"
