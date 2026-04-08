#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

CI_LOG_FILE="$DEVOS_LOG_DIR/ci.log"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_TMP_DIR" "$DEVOS_HOME/runtime/ci"

ci_log() {
  printf '%s [CI] %s\n' "$(date '+%F %T')" "$*" >> "$CI_LOG_FILE"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    ci_log "missing required command: $cmd"
    printf 'Missing required command: %s\n' "$cmd" >&2
    exit 127
  fi
}

state_get() {
  "$DEVOS_HOME/ops/state_manager.py" get "$1" | tr -d '"'
}

state_set() {
  "$DEVOS_HOME/ops/state_manager.py" set "$1" "$2" || true
}

state_touch() {
  "$DEVOS_HOME/ops/state_manager.py" touch "$1" || true
}

ci_repo_path() {
  local repo
  repo="$(state_get ci.repo_path)"
  if [[ -z "$repo" || "$repo" == "null" ]]; then
    readarray -t project_info < <("$DEVOS_HOME/bin/project-dispatcher.sh")
    repo="${project_info[1]}"
  fi
  printf '%s\n' "$repo"
}

ci_default_branch() {
  local branch
  branch="$(state_get ci.default_branch)"
  if [[ -z "$branch" || "$branch" == "null" ]]; then
    branch="$GITHUB_BASE_BRANCH"
  fi
  printf '%s\n' "$branch"
}

ensure_repo() {
  local repo="$1"
  if [[ ! -d "$repo/.git" ]]; then
    ci_log "not a git repository: $repo"
    printf 'Not a git repository: %s\n' "$repo" >&2
    exit 1
  fi
}
