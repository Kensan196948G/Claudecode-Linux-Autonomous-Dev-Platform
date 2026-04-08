#!/usr/bin/env bash
set -euo pipefail

DEVOS_HOME="${DEVOS_HOME:-/opt/claudecode-devos}"
# shellcheck source=/dev/null
source "$DEVOS_HOME/config/devos.env"

python3 - "$DEVOS_PROJECTS_FILE" "${DEVOS_SELECTED_PROJECT_FILE:-}" "${DEVOS_USE_SELECTED_PROJECT:-false}" <<'PY'
import json
import sys
from datetime import date, datetime
from pathlib import Path

projects_file = Path(sys.argv[1])
selected_file = Path(sys.argv[2]) if sys.argv[2] else None
use_selected = sys.argv[3].lower() == "true"
data = json.loads(projects_file.read_text(encoding="utf-8"))
projects = data.get("projects", [])

if use_selected and selected_file and selected_file.exists():
    selected = json.loads(selected_file.read_text(encoding="utf-8"))
    if selected.get("id"):
        print(selected["id"])
        print(selected["repository"])
        print(selected["docs_dir"])
        print(selected.get("session_prompt_file", ""))
        raise SystemExit(0)

def parse_date(value):
    if not value:
        return date.max
    return datetime.strptime(value, "%Y-%m-%d").date()

today = date.today()
active = []
for project in projects:
    if project.get("status") != "active":
        continue
    due = project.get("release_due")
    if due and parse_date(due) < today:
        continue
    active.append(project)

if not active:
    raise SystemExit("No active projects")

priority_rank = {"high": 0, "medium": 1, "low": 2}
active.sort(key=lambda x: (priority_rank.get(x.get("priority"), 99), x.get("registered_at", "")))
target = active[0]

print(target["id"])
print(target["repository"])
print(target["docs_dir"])
print(target.get("session_prompt_file", ""))
PY
