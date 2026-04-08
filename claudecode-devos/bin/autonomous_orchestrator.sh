#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

LOG_FILE="$DEVOS_LOG_DIR/orchestrator.log"
mkdir -p "$DEVOS_LOG_DIR"

log() {
  printf '%s [ORCH] %s\n' "$(date '+%F %T')" "$*" >> "$LOG_FILE"
}

log "cycle start"
ORCH_START="$(date +%s)"

"$DEVOS_HOME/ops/usage_manager.py" reset >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ops/usage_manager.py" check >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ops/memory_guard.py" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ci/check_ci_status.sh" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ops/harness_checks.py" --phase Monitor --skip-quality >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ops/stable_gate.py" evaluate >> "$LOG_FILE" 2>&1 || true
NEXT_ACTION="$("$DEVOS_HOME/ops/decision_engine.py" 2>> "$LOG_FILE" || printf 'idle')"
NEXT_ACTION="$(python3 - "$DEVOS_STATE_FILE" "$NEXT_ACTION" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
fallback = sys.argv[2]
control = state.get("control", {})
if control.get("manual_override") and control.get("manual_action"):
    print(control["manual_action"])
else:
    print(fallback)
PY
)"

if [[ "$NEXT_ACTION" == "repair_ci" ]]; then
  "$DEVOS_HOME/ai/issue_factory.py" >> "$LOG_FILE" 2>&1 || true
  "$DEVOS_HOME/ai/issue_prioritizer.py" >> "$LOG_FILE" 2>&1 || true
  "$DEVOS_HOME/ai/prompt_builder.py" >> "$LOG_FILE" 2>&1 || true
fi

log "next_action=$NEXT_ACTION"

case "$NEXT_ACTION" in
  develop)
    "$DEVOS_HOME/bin/run-scheduled-project.sh" >> "$LOG_FILE" 2>&1 || true
    ;;
  repair_ci)
    "$DEVOS_HOME/ci/fetch_ci_failure.sh" >> "$LOG_FILE" 2>&1 || true
    "$DEVOS_HOME/ci/repair_ci_worktree.sh" >> "$LOG_FILE" 2>&1 || true
    ;;
  cooldown)
    log "cooldown ${DECISION_COOLDOWN_SECONDS}s"
    sleep "$DECISION_COOLDOWN_SECONDS"
    ;;
  suspend)
    log "suspended by policy"
    ;;
  *)
    log "idle"
    ;;
esac

"$DEVOS_HOME/ops/harness_checks.py" --phase Verify >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ops/stable_gate.py" evaluate >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ci/merge_green_prs.sh" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/ai/agent_logger.sh" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/evolution/log_collector.py" "orchestrator_cycle" "success" "$(($(date +%s) - ORCH_START))" --detail "{\"next_action\":\"$NEXT_ACTION\"}" >> "$LOG_FILE" 2>&1 || true
"$DEVOS_HOME/core/evolution_loop.py" >> "$LOG_FILE" 2>&1 || true
log "cycle end"
