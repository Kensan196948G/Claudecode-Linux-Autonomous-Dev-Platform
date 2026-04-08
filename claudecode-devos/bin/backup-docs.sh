#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

TODAY="$(date +%F)"
DEST="$ARCHIVE_ROOT/$TODAY"
SRC="$DEVOS_HOME/docs"

mkdir -p "$DEST" "$DEVOS_LOG_DIR"
rsync -a --delete "$SRC/" "$DEST/docs/"

echo "$(date '+%F %T') [BACKUP] docs backed up to $DEST/docs" >> "$DEVOS_LOG_DIR/backup.log"
