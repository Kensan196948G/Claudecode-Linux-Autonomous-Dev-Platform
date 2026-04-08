#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG_FILE="$DEVOS_LOG_DIR/session.log"
mkdir -p "$DEVOS_LOG_DIR" "$DEVOS_TMP_DIR"

readarray -t PROJECT_INFO < <("$DEVOS_HOME/bin/project-dispatcher.sh")

PROJECT_ID="${PROJECT_INFO[0]}"
PROJECT_REPO="${PROJECT_INFO[1]}"
PROJECT_DOCS="${PROJECT_INFO[2]}"
PROJECT_PROMPT="${PROJECT_INFO[3]}"
SESSION_CONTEXT="$PROJECT_DOCS/session_context.md"
COMPOSED_PROMPT="$DEVOS_TMP_DIR/claude-session-${PROJECT_ID}.md"

echo "$(date '+%F %T') [SESSION] start project=$PROJECT_ID" >> "$LOG_FILE"

if ! USAGE_CHECK_OUTPUT="$("$DEVOS_HOME/ops/usage_manager.py" check 2>&1)"; then
  echo "$(date '+%F %T') [SESSION] skipped project=$PROJECT_ID reason=$USAGE_CHECK_OUTPUT" >> "$LOG_FILE"
  "$DEVOS_HOME/ops/state_manager.py" set system.status idle
  "$DEVOS_HOME/ops/state_manager.py" set claude.status stopped
  "$DEVOS_HOME/notifications/notifier.py" "LIMIT" "$USAGE_CHECK_OUTPUT" || true
  exit 0
fi
echo "$(date '+%F %T') [SESSION] usage check: $USAGE_CHECK_OUTPUT" >> "$LOG_FILE"

"$DEVOS_HOME/ops/state_manager.py" set projects.active_project "$PROJECT_ID"
"$DEVOS_HOME/ops/state_manager.py" touch projects.last_project_switch
"$DEVOS_HOME/ops/state_manager.py" touch system.last_session_start
"$DEVOS_HOME/ops/state_manager.py" set system.status running
"$DEVOS_HOME/ops/state_manager.py" set claude.status starting

if [[ ! -d "$PROJECT_REPO" ]]; then
  echo "$(date '+%F %T') [ERROR] repository not found: $PROJECT_REPO" >> "$LOG_FILE"
  "$DEVOS_HOME/ops/state_manager.py" set system.last_error "repository not found: $PROJECT_REPO"
  "$DEVOS_HOME/ops/state_manager.py" set system.status idle
  exit 1
fi

cd "$PROJECT_REPO"
mkdir -p "$PROJECT_DOCS"

cat > "$SESSION_CONTEXT" <<CTX
# Session Context

- Project ID: $PROJECT_ID
- Start: $(date '+%F %T')
- Session Limit: ${SESSION_MAX_SECONDS}s
- Prompt File: $PROJECT_PROMPT
- DevOS State File: $DEVOS_STATE_FILE

## Runtime Rules
- Use Claude through claude-safe.
- Respect the 5-hour runtime limit.
- Update Docs continuously.
- Prefer safe mode if memory pressure exists.
CTX

{
  printf '# ClaudeCode DevOS Session\n\n'
  cat "$SESSION_CONTEXT"
  printf '\n\n## Current DevOS State\n\n```json\n'
  cat "$DEVOS_STATE_FILE"
  printf '\n```\n'
  if [[ -n "$PROJECT_PROMPT" && -f "$PROJECT_PROMPT" ]]; then
    printf '\n\n## Project Start Prompt\n\n'
    cat "$PROJECT_PROMPT"
  else
    printf '\n\n## Project Start Prompt\n\nNo START_PROMPT.md was found. Inspect Docs, state.json, git status, and continue the safest next task.\n'
  fi
} > "$COMPOSED_PROMPT"

START_TIME="$(date +%s)"
set +e
timeout "$SESSION_MAX_SECONDS" "$DEVOS_HOME/bin/claude-safe.sh" < "$COMPOSED_PROMPT"
RC=$?
set -e
END_TIME="$(date +%s)"
DURATION="$((END_TIME - START_TIME))"

if ! USAGE_RECORD_OUTPUT="$("$DEVOS_HOME/ops/usage_manager.py" record "$DURATION" 2>&1)"; then
  echo "$(date '+%F %T') [SESSION] usage limit reached after duration=${DURATION}s message=$USAGE_RECORD_OUTPUT" >> "$LOG_FILE"
else
  echo "$(date '+%F %T') [SESSION] usage recorded duration=${DURATION}s message=$USAGE_RECORD_OUTPUT" >> "$LOG_FILE"
fi

"$DEVOS_HOME/ops/state_manager.py" set claude.status stopped
"$DEVOS_HOME/ops/state_manager.py" set system.status idle
"$DEVOS_HOME/ops/state_manager.py" touch system.last_session_end

if [[ "$RC" -eq 124 ]]; then
  echo "$(date '+%F %T') [SESSION] timeout project=$PROJECT_ID" >> "$LOG_FILE"
else
  echo "$(date '+%F %T') [SESSION] end project=$PROJECT_ID rc=$RC" >> "$LOG_FILE"
fi

exit 0
