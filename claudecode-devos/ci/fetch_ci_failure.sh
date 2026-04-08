#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/ci/common.sh"

require_cmd gh
require_cmd python3

REPO_PATH="$(ci_repo_path)"
RUN_ID="$(state_get ci.last_run_id)"
ensure_repo "$REPO_PATH"

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  printf 'CI run id not found.\n' > "$DEVOS_HOME/runtime/ci/last_failure_summary.txt"
  ci_log "failure fetch skipped; run id not found"
  exit 0
fi

cd "$REPO_PATH"
ci_log "fetch failure repo=$REPO_PATH run=$RUN_ID"

gh run view "$RUN_ID" --log > "$DEVOS_HOME/runtime/ci/last_failure.log" || true

python3 - "$DEVOS_HOME/runtime/ci/last_failure.log" "$DEVOS_HOME/runtime/ci/last_failure_summary.txt" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

if not src.exists():
    dst.write_text("CI log not found.\n", encoding="utf-8")
    raise SystemExit(0)

text = src.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()
keywords = ("error", "failed", "exception", "traceback", "npm ERR", "pytest", "AssertionError")
picked = [line for line in lines if any(k.lower() in line.lower() for k in keywords)]

if not picked:
    picked = lines[-80:]

dst.write_text("\n".join(picked[:200]) + "\n", encoding="utf-8")
PY
