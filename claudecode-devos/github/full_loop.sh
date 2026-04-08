#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/github/common.sh"

REPO="$(resolve_repo "${1:-}")"
ensure_repo "$REPO"

while true; do
  github_log "loop start repo=$REPO"

  if ! "$DEVOS_HOME/ops/usage_manager.py" check >> "$GITHUB_LOG_FILE" 2>&1; then
    github_log "loop skipped by usage limit"
  else
    mapfile -t ISSUE_INFO < <("$DEVOS_HOME/github/issue_manager.sh" "$REPO")
    ISSUE_NUMBER="${ISSUE_INFO[0]:-}"
    if [[ -z "$ISSUE_NUMBER" ]]; then
      github_log "loop idle; no open issue"
    else
      BRANCH="$("$DEVOS_HOME/github/sync.sh" "$REPO" "$ISSUE_NUMBER" | tail -n 1)"
      if [[ -n "$BRANCH" ]]; then
        "$DEVOS_HOME/github/pr_manager.sh" "$REPO" "$BRANCH" "$ISSUE_NUMBER" >> "$GITHUB_LOG_FILE" 2>&1
      else
        github_log "loop skipped pr; sync produced no branch issue=$ISSUE_NUMBER"
      fi
    fi
  fi

  if [[ "$GITHUB_LOOP_ONCE" == "true" ]]; then
    break
  fi
  sleep "$GITHUB_LOOP_SLEEP_SECONDS"
done
