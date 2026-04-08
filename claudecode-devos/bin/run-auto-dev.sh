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

"$DEVOS_HOME/bin/sync-claudeos-template.sh" "$(pwd)/.claude/claudeos" >> "$LOG" 2>&1 || {
  "$DEVOS_HOME/ops/state_manager.py" set decision.next_action suspend
  "$DEVOS_HOME/ops/state_manager.py" set system.last_error "ClaudeOS template sync failed"
  exit 1
}
if [[ -d .git ]]; then
  mkdir -p .git/info
  touch .git/info/exclude
  grep -qxF ".claude/claudeos/" .git/info/exclude || printf '%s\n' ".claude/claudeos/" >> .git/info/exclude
fi

"$DEVOS_HOME/ai/prompt_builder.py" >/dev/null

printf '%s [DEV] start prompt=%s\n' "$(date '+%F %T')" "$PROMPT" >> "$LOG"
if [[ "${DEVOS_CLAUDE_FOREGROUND:-false}" == "true" ]]; then
  printf '[DevOS] prompt=%s\n' "$PROMPT"
  printf '[DevOS] launching Claude CLI...\n'
  timeout --foreground "$AUTO_DEV_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" "$(cat "$PROMPT")" || true
else
  timeout "$AUTO_DEV_TIMEOUT_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" "$(cat "$PROMPT")" >> "$LOG" 2>&1 || true
fi
"$DEVOS_HOME/ops/harness_checks.py" --repo "$(pwd)" --phase Verify >> "$LOG" 2>&1 || true
"$DEVOS_HOME/ops/stable_gate.py" evaluate >> "$LOG" 2>&1 || true
printf '%s [DEV] end\n' "$(date '+%F %T')" >> "$LOG"
