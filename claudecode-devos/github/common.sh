#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

GITHUB_LOG_FILE="$DEVOS_LOG_DIR/github.log"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_TMP_DIR"

github_log() {
  printf '%s [GITHUB] %s\n' "$(date '+%F %T')" "$*" >> "$GITHUB_LOG_FILE"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    github_log "missing required command: $cmd"
    printf 'Missing required command: %s\n' "$cmd" >&2
    exit 127
  fi
}

state_set() {
  "$DEVOS_HOME/ops/state_manager.py" set "$1" "$2" || true
}

state_touch() {
  "$DEVOS_HOME/ops/state_manager.py" touch "$1" || true
}

resolve_repo() {
  if [[ "${1:-}" != "" ]]; then
    printf '%s\n' "$1"
    return 0
  fi

  readarray -t project_info < <("$DEVOS_HOME/bin/project-dispatcher.sh")
  printf '%s\n' "${project_info[1]}"
}

ensure_repo() {
  local repo="$1"
  if [[ ! -d "$repo/.git" ]]; then
    github_log "not a git repository: $repo"
    printf 'Not a git repository: %s\n' "$repo" >&2
    exit 1
  fi
}
