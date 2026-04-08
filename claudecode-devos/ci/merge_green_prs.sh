#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/ci/common.sh"

require_cmd gh
require_cmd python3

"$DEVOS_HOME/ops/stable_gate.py" evaluate >> "$CI_LOG_FILE" 2>&1 || true
STABLE="$(state_get ci.stable)"
if [[ "$STABLE" != "true" ]]; then
  ci_log "merge skipped; STABLE gate is not satisfied"
  exit 0
fi

AUTO_MERGE="$(state_get ci.auto_merge_enabled)"
if [[ "$AUTO_MERGE" != "true" && "$CI_AUTO_MERGE" != "true" ]]; then
  ci_log "merge skipped; auto merge disabled"
  exit 0
fi

REPO_PATH="$(ci_repo_path)"
ensure_repo "$REPO_PATH"
cd "$REPO_PATH"

ci_log "merge green prs repo=$REPO_PATH"

python3 - <<'PY'
import json
import subprocess
import sys

prs = json.loads(
    subprocess.check_output(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--json",
            "number,mergeStateStatus,reviewDecision,headRefName,statusCheckRollup",
        ],
        text=True,
    )
)

for pr in prs:
    number = str(pr["number"])
    merge_state = pr.get("mergeStateStatus")
    review = pr.get("reviewDecision")
    checks = pr.get("statusCheckRollup") or []
    failed = [
        check.get("name") or check.get("context") or "unknown"
        for check in checks
        if (check.get("conclusion") or check.get("status")) not in ("SUCCESS", "COMPLETED", "SKIPPED", None)
    ]
    if failed:
        print(f"skip PR #{number}; checks not green: {failed}", file=sys.stderr)
        continue
    if merge_state == "CLEAN" and review == "APPROVED":
        subprocess.run(["gh", "pr", "merge", number, "--squash", "--delete-branch"], check=False)
    else:
        print(f"skip PR #{number}; merge_state={merge_state} review={review}", file=sys.stderr)
PY
