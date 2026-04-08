#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"
: "${CLAUDE_CMD:?CLAUDE_CMD is required}"

LOG_FILE="$DEVOS_LOG_DIR/claude-safe.log"
PID_FILE="$DEVOS_PID_DIR/claude.pid"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_PID_DIR"

log() {
  printf '%s [INFO] %s\n' "$(date '+%F %T')" "$*" >> "$LOG_FILE"
}

log "claude-safe starting"

if ! command -v "$CLAUDE_CMD" >/dev/null 2>&1; then
  log "Claude command not found: $CLAUDE_CMD"
  "$DEVOS_HOME/ops/state_manager.py" set claude.status error || true
  "$DEVOS_HOME/ops/state_manager.py" set system.last_error "Claude command not found: $CLAUDE_CMD" || true
  exit 127
fi

ulimit -v "$CLAUDE_MEMORY_LIMIT_KB"

if [[ -w /proc/$$/oom_score_adj ]]; then
  printf '%s\n' "$CLAUDE_OOM_SCORE_ADJ" > /proc/$$/oom_score_adj || true
fi

read -r -a CLAUDE_OPTION_ARGS <<< "$CLAUDE_OPTIONS"
CMD=(
  ionice -c "$CLAUDE_IONICE_CLASS" -n "$CLAUDE_IONICE_PRIO"
  nice -n "$CLAUDE_NICE"
  "$CLAUDE_CMD"
  "${CLAUDE_OPTION_ARGS[@]}"
  "$@"
)

log "command: ${CMD[*]}"

"${CMD[@]}" >> "$LOG_FILE" 2>&1 &
CLAUDE_PID=$!
printf '%s\n' "$CLAUDE_PID" > "$PID_FILE"

"$DEVOS_HOME/ops/state_manager.py" set claude.status running || true
"$DEVOS_HOME/ops/state_manager.py" set claude.last_pid "$CLAUDE_PID" || true
"$DEVOS_HOME/ops/state_manager.py" set claude.last_command "${CMD[*]}" || true

log "Claude PID=$CLAUDE_PID"

set +e
wait "$CLAUDE_PID"
RC=$?
set -e

rm -f "$PID_FILE"
"$DEVOS_HOME/ops/state_manager.py" set claude.status stopped || true

log "Claude exited rc=$RC"
exit "$RC"
