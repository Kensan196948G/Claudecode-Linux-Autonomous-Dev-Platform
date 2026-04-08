#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/ci/common.sh"

require_cmd gh
require_cmd python3

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

prs = json.loads(
    subprocess.check_output(
        ["gh", "pr", "list", "--state", "open", "--json", "number,mergeStateStatus,reviewDecision,headRefName"],
        text=True,
    )
)

for pr in prs:
    number = str(pr["number"])
    merge_state = pr.get("mergeStateStatus")
    review = pr.get("reviewDecision")
    if merge_state == "CLEAN" and review in ("APPROVED", None, ""):
        subprocess.run(["gh", "pr", "merge", number, "--squash", "--delete-branch"], check=False)
PY
