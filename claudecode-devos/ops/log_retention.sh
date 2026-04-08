#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

mkdir -p "$DEVOS_LOG_ARCHIVE_DIR"

find "$DEVOS_LOG_DIR" -type f -name '*.log' -mtime +"$LOG_RETENTION_DAYS" -print0 |
while IFS= read -r -d '' file; do
  rel="${file#"$DEVOS_LOG_DIR"/}"
  archive="$DEVOS_LOG_ARCHIVE_DIR/${rel//\//_}.$(date +%Y%m%d%H%M%S).gz"
  gzip -c "$file" > "$archive"
  : > "$file"
done

find "$DEVOS_LOG_ARCHIVE_DIR" -type f -name '*.gz' -mtime +"$ARCHIVE_RETENTION_DAYS" -delete

printf '%s [LOG_RETENTION] complete logs>%sd archive>%sd\n' "$(date '+%F %T')" "$LOG_RETENTION_DAYS" "$ARCHIVE_RETENTION_DAYS" >> "$DEVOS_LOG_DIR/log-retention.log"
