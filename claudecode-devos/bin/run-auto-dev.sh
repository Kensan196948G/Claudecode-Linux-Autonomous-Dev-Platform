#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

PROMPT="$DEVOS_HOME/runtime/prompts/current_prompt.md"
LOG="$DEVOS_HOME/runtime/agent_logs/development.log"
mkdir -p "$(dirname "$LOG")" "$DEVOS_HOME/runtime/prompts"

if [[ "${AUTO_DEV_REPO:-}" != "" ]]; then
  cd "$AUTO_DEV_REPO"
fi

if [[ ! -s "$PROMPT" ]]; then
  "$DEVOS_HOME/ai/prompt_builder.py" >/dev/null
fi

printf '%s [DEV] start prompt=%s\n' "$(date '+%F %T')" "$PROMPT" >> "$LOG"
if [[ "${DEVOS_CLAUDE_FOREGROUND:-false}" == "true" ]]; then
  printf '[DevOS] prompt=%s\n' "$PROMPT"
  printf '[DevOS] launching Claude CLI...\n'
  timeout --foreground "$AUTO_DEV_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" "$(cat "$PROMPT")" || true
else
  timeout "$AUTO_DEV_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" < "$PROMPT" >> "$LOG" 2>&1 || true
fi
printf '%s [DEV] end\n' "$(date '+%F %T')" >> "$LOG"
