#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
SRC="$DEVOS_HOME/templates/claudeos"
DEST="${1:-.claude/claudeos}"

if [[ ! -d "$SRC" ]]; then
  printf '[DevOS] ClaudeOS template source not found: %s\n' "$SRC" >&2
  exit 1
fi

case "$DEST" in
  ""|"/"|".")
    printf '[DevOS] refusing unsafe ClaudeOS template destination: %s\n' "$DEST" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SRC" "$DEST"

printf '[DevOS] ClaudeOS template synced: %s -> %s (%s files)\n' \
  "$SRC" \
  "$DEST" \
  "$(find "$DEST" -type f | wc -l)"
