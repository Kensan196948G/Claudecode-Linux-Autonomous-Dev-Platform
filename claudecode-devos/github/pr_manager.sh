#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/github/common.sh"

require_cmd git
require_cmd gh

REPO="$(resolve_repo "${1:-}")"
BRANCH="${2:-}"
ISSUE_NUMBER="${3:-}"
ensure_repo "$REPO"
cd "$REPO"

if [[ -z "$BRANCH" || "$BRANCH" == "null" ]]; then
  BRANCH="$("$DEVOS_HOME/ops/state_manager.py" get github.current_branch | tr -d '"')"
fi
if [[ -z "$ISSUE_NUMBER" || "$ISSUE_NUMBER" == "null" ]]; then
  ISSUE_NUMBER="$("$DEVOS_HOME/ops/state_manager.py" get github.current_issue | tr -d '"')"
fi
if [[ -z "$BRANCH" || "$BRANCH" == "null" ]]; then
  github_log "pr skipped; no branch repo=$REPO"
  state_set github.last_error "pr skipped; no branch"
  exit 0
fi

if ! git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  github_log "pr skipped; branch not found branch=$BRANCH"
  state_set github.last_error "pr skipped; branch not found"
  exit 0
fi

git checkout "$BRANCH" >> "$GITHUB_LOG_FILE" 2>&1
git push -u origin "$BRANCH" >> "$GITHUB_LOG_FILE" 2>&1

PR_URL="$(gh pr view "$BRANCH" --json url --jq .url 2>/dev/null || true)"
if [[ -z "$PR_URL" ]]; then
  TITLE="Auto PR by ClaudeCode DevOS"
  BODY="Auto-generated implementation from ClaudeCode DevOS."
  if [[ -n "$ISSUE_NUMBER" && "$ISSUE_NUMBER" != "null" ]]; then
    TITLE="Auto: address issue #${ISSUE_NUMBER}"
    BODY="Auto-generated implementation for #${ISSUE_NUMBER}."
  fi
  PR_URL="$(gh pr create --title "$TITLE" --body "$BODY" --base "$GITHUB_BASE_BRANCH" --head "$BRANCH")"
fi

state_set github.last_pr "$PR_URL"
state_set github.auto_merge_enabled "$GITHUB_AUTO_MERGE"
github_log "pr ready branch=$BRANCH url=$PR_URL auto_merge=$GITHUB_AUTO_MERGE"

if [[ "$GITHUB_AUTO_MERGE" == "true" ]]; then
  sleep "$GITHUB_CI_WAIT_SECONDS"
  gh pr merge "$BRANCH" --auto --squash --delete-branch
  state_set github.ci_status "auto_merge_requested"
  github_log "auto merge requested branch=$BRANCH"
else
  state_set github.ci_status "pr_open_auto_merge_disabled"
fi

printf '%s\n' "$PR_URL"
