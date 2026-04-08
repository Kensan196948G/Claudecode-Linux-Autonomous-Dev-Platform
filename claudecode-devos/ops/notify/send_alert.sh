#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

SUBJECT="${1:-[ALERT] ClaudeCode DevOS}"
BODY="${2:-}"

if [[ "$ALERT_MAIL_ENABLED" != "true" || -z "$ALERT_MAIL_TO" ]]; then
  exit 0
fi

mkdir -p "$DEVOS_LOG_DIR"

if ! command -v mail >/dev/null 2>&1; then
  printf '%s [WARN] mail command not found; alert skipped subject=%s\n' "$(date '+%F %T')" "$SUBJECT" >> "$DEVOS_LOG_DIR/notify.log"
  exit 0
fi

printf '%s\n' "$BODY" | mail -s "$SUBJECT" "$ALERT_MAIL_TO"
printf '%s [INFO] alert sent subject=%s to=%s\n' "$(date '+%F %T')" "$SUBJECT" "$ALERT_MAIL_TO" >> "$DEVOS_LOG_DIR/notify.log"
