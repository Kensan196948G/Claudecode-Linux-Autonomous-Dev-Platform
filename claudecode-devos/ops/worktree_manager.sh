#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

ACTION="${1:-}"
REPO_PATH="${2:-}"
BRANCH_NAME="${3:-}"
WT_TYPE="${4:-feature}"

if [[ -z "$ACTION" || -z "$REPO_PATH" ]]; then
  echo "Usage: worktree_manager.sh <create|remove> <repo_path> [branch_name] [type]" >&2
  exit 1
fi

BASE_DIR="$("$DEVOS_HOME/ops/state_manager.py" get worktree.base_dir | tr -d '"')"
if [[ -z "$BASE_DIR" || "$BASE_DIR" == "null" || ( "$DEVOS_HOME" != "/opt/claudecode-devos" && "$BASE_DIR" == "/opt/claudecode-devos/runtime/worktrees" ) ]]; then
  BASE_DIR="$WORKTREE_BASE_DIR"
fi

if [[ -z "$BRANCH_NAME" || "$BRANCH_NAME" == "null" ]]; then
  BRANCH_NAME="${WT_TYPE}/auto-$(date +%Y%m%d-%H%M%S)"
fi

mkdir -p "$BASE_DIR"

REPO_NAME="$(basename "$REPO_PATH" | tr -cd '[:alnum:]_.-')"
SAFE_BRANCH="$(printf '%s' "$BRANCH_NAME" | tr '/:' '--' | tr -cd '[:alnum:]_.-')"
WT_PATH="$BASE_DIR/${REPO_NAME}-${WT_TYPE}-${SAFE_BRANCH}"

set_worktree_state() {
  "$DEVOS_HOME/ops/state_manager.py" set worktree.current_path "$1"
  "$DEVOS_HOME/ops/state_manager.py" set worktree.current_branch "$2"
  "$DEVOS_HOME/ops/state_manager.py" set worktree.current_type "$3"
}

case "$ACTION" in
  create)
    if [[ ! -d "$REPO_PATH/.git" ]]; then
      echo "Not a git repository: $REPO_PATH" >&2
      exit 1
    fi
    cd "$REPO_PATH"
    git fetch origin >/dev/null 2>&1 || true

    if [[ -d "$WT_PATH" ]]; then
      git worktree remove "$WT_PATH" --force >/dev/null 2>&1 || true
    fi

    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
      git worktree add "$WT_PATH" "$BRANCH_NAME" >/dev/null 2>&1
    else
      git worktree add -b "$BRANCH_NAME" "$WT_PATH" HEAD >/dev/null 2>&1
    fi

    set_worktree_state "$WT_PATH" "$BRANCH_NAME" "$WT_TYPE"
    printf '%s\n' "$WT_PATH"
    ;;
  remove)
    if [[ -d "$REPO_PATH/.git" ]]; then
      cd "$REPO_PATH"
      if [[ -d "$WT_PATH" ]]; then
        git worktree remove "$WT_PATH" --force >/dev/null 2>&1 || true
      fi
      git worktree prune >/dev/null 2>&1 || true
    fi
    set_worktree_state null null null
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 1
    ;;
esac
