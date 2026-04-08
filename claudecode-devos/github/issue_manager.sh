#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/github/common.sh"

require_cmd gh
require_cmd python3

REPO="$(resolve_repo "${1:-}")"
ensure_repo "$REPO"
cd "$REPO"

ISSUES_FILE="$DEVOS_TMP_DIR/github-issues.json"
github_log "fetch issues repo=$REPO limit=$GITHUB_ISSUE_LIMIT"

gh issue list --state open --limit "$GITHUB_ISSUE_LIMIT" --json number,title,url > "$ISSUES_FILE"

python3 - "$DEVOS_STATE_FILE" "$ISSUES_FILE" "$REPO" "$DEVOS_LOCK_DIR/state.lock" <<'PY'
import fcntl
import json
import sys
from datetime import datetime
from pathlib import Path

state_file = Path(sys.argv[1])
issues_file = Path(sys.argv[2])
repo = sys.argv[3]
lock_file = Path(sys.argv[4])
issues = json.loads(issues_file.read_text(encoding="utf-8"))
lock_file.parent.mkdir(parents=True, exist_ok=True)
with lock_file.open("w", encoding="utf-8") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = json.loads(state_file.read_text(encoding="utf-8"))
    github = state.setdefault("github", {})
    github["repo"] = repo
    github["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if issues:
        issue = issues[0]
        github["current_issue"] = issue.get("number")
        github["current_issue_title"] = issue.get("title")
        github["last_error"] = None
        print(issue.get("number"))
        print(issue.get("title"))
    else:
        github["current_issue"] = None
        github["current_issue_title"] = None
        print("")
        print("")
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
