#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/github/common.sh"

require_cmd git
require_cmd gh

REPO="$(resolve_repo "${1:-}")"
ISSUE_NUMBER="${2:-}"
ensure_repo "$REPO"
cd "$REPO"

if [[ -z "$ISSUE_NUMBER" || "$ISSUE_NUMBER" == "null" ]]; then
  ISSUE_NUMBER="$("$DEVOS_HOME/ops/state_manager.py" get github.current_issue | tr -d '"')"
fi

if [[ -z "$ISSUE_NUMBER" || "$ISSUE_NUMBER" == "null" ]]; then
  github_log "sync skipped; no current issue repo=$REPO"
  exit 0
fi

SAFE_REPO_ID="$(basename "$REPO" | tr -cd '[:alnum:]_.-')"
BRANCH="feature/auto-issue-${ISSUE_NUMBER}-$(date +%s)"
PROMPT_FILE="$DEVOS_TMP_DIR/github-issue-${SAFE_REPO_ID}-${ISSUE_NUMBER}.md"
ISSUE_FILE="$DEVOS_TMP_DIR/github-issue-${SAFE_REPO_ID}-${ISSUE_NUMBER}.json"

github_log "sync start repo=$REPO issue=$ISSUE_NUMBER base=$GITHUB_BASE_BRANCH branch=$BRANCH"

git fetch origin "$GITHUB_BASE_BRANCH" >> "$GITHUB_LOG_FILE" 2>&1
git checkout -B "$BRANCH" "origin/$GITHUB_BASE_BRANCH" >> "$GITHUB_LOG_FILE" 2>&1

gh issue view "$ISSUE_NUMBER" --json number,title,body,url > "$ISSUE_FILE"

python3 - "$ISSUE_FILE" "$DEVOS_STATE_FILE" > "$PROMPT_FILE" <<'PY'
import json
import sys
from pathlib import Path

issue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
state = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
print("# ClaudeCode DevOS GitHub Issue Session")
print()
print(f"- Issue: #{issue['number']} {issue['title']}")
print(f"- URL: {issue.get('url', '')}")
print()
print("## Issue Body")
print(issue.get("body") or "(no body)")
print()
print("## Current DevOS State")
print("```json")
print(json.dumps(state, ensure_ascii=False, indent=2))
print("```")
print()
print("## Rules")
print("- Work on this feature branch only.")
print("- Implement the smallest safe change for the issue.")
print("- Run focused tests or validation when available.")
print("- Update relevant Docs when behavior or operations change.")
print("- Do not push to the base branch directly.")
PY

"$DEVOS_HOME/bin/claude-safe.sh" < "$PROMPT_FILE"

if [[ -z "$(git status --porcelain)" ]]; then
  github_log "no changes after claude execution issue=$ISSUE_NUMBER"
  state_set github.current_branch null
  state_set github.last_error "no changes after claude execution"
  exit 0
fi

git add .
git commit -m "auto: address issue #${ISSUE_NUMBER}" >> "$GITHUB_LOG_FILE" 2>&1
state_set github.current_branch "$BRANCH"
state_set github.last_error null
state_touch github.last_sync
github_log "sync committed branch=$BRANCH issue=$ISSUE_NUMBER"
printf '%s\n' "$BRANCH"
