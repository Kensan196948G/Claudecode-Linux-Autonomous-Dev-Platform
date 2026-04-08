#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG_FILE="$DEVOS_LOG_DIR/recovery.log"
LOCK_FILE="$DEVOS_LOCK_DIR/recovery.lock"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_LOCK_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date '+%F %T') [RECOVERY] skipped; another recovery is running" >> "$LOG_FILE"
  exit 0
fi

log() {
  printf '%s [RECOVERY] %s\n' "$(date '+%F %T')" "$*" >> "$LOG_FILE"
}

stop_pid_file_process() {
  local pid_file="$1"
  local name="$2"
  if [[ ! -s "$pid_file" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    log "stopping $name pid=$pid"
    kill -15 "$pid" 2>/dev/null || true
    sleep 3
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

log "start"

pkill -15 -u "$(id -u)" -f '(^|[ /])pytest([ ]|$)|python[0-9.]* .*pytest' || true
sleep 5
pkill -9 -u "$(id -u)" -f '(^|[ /])pytest([ ]|$)|python[0-9.]* .*pytest' || true
log "pytest stopped if existed"

stop_pid_file_process "$DEVOS_PID_DIR/claude.pid" "claude"
log "claude pid-file process stopped if existed"

if command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    sudo -n swapoff -a || true
    sudo -n swapon -a || true
    log "swap refreshed"
  else
    log "swap refresh skipped; sudo requires interaction"
  fi
fi

"$DEVOS_HOME/ops/state_manager.py" set system.last_error OOM
"$DEVOS_HOME/ops/state_manager.py" set system.health warning
"$DEVOS_HOME/ops/state_manager.py" touch system.last_recovery
"$DEVOS_HOME/ops/state_manager.py" inc system.recovery_count

log "state updated"

if [[ "$DEVOS_AUTO_RESTART_CLAUDE" == "true" ]]; then
  nohup "$DEVOS_HOME/bin/claude-safe.sh" >/dev/null 2>&1 &
  log "claude-safe restarted"
else
  log "claude-safe restart skipped by DEVOS_AUTO_RESTART_CLAUDE"
fi

log "end"
