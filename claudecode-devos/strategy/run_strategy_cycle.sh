#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG="$DEVOS_LOG_DIR/strategy.log"
mkdir -p "$DEVOS_LOG_DIR"

{
  echo "$(date '+%F %T') [STRATEGY] cycle start"
  "$DEVOS_HOME/strategy/score_projects.py"
  "$DEVOS_HOME/strategy/select_projects.py"
  echo "$(date '+%F %T') [STRATEGY] cycle end"
} >> "$LOG" 2>&1
