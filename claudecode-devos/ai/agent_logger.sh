#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG_DIR="$DEVOS_HOME/runtime/agent_logs"
OUT="$LOG_DIR/agent_timeline.log"
mkdir -p "$LOG_DIR"

printf '===== %s =====\n' "$(date '+%F %T')" >> "$OUT"

for log_file in monitor.log development.log verify.log repair-ci.log; do
  if [[ -f "$LOG_DIR/$log_file" ]]; then
    printf '%s\n' "--- $log_file ---" >> "$OUT"
    tail -20 "$LOG_DIR/$log_file" >> "$OUT"
  fi
done

"$DEVOS_HOME/ops/state_manager.py" touch ai.last_agent_log_at || true
