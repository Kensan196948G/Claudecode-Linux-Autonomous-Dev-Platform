#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

PHASE="${1:-unknown}"
MESSAGE="${2:-}"
LOG_FILE="$DEVOS_HOME/runtime/agent_logs/agent_events.log"

mkdir -p "$(dirname "$LOG_FILE")"
printf '%s [%s] %s\n' "$(date '+%F %T')" "$PHASE" "$MESSAGE" >> "$LOG_FILE"
