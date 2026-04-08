#!/usr/bin/env python3
import fcntl
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
OUT = DEVOS_HOME / "runtime/issues/selected_issue.json"
ISSUE_LIMIT = os.environ.get("ISSUE_PRIORITY_LIMIT", "20")


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def score(issue):
    value = 0
    title = (issue.get("title") or "").lower()
    labels = [(label.get("name") or "").lower() for label in issue.get("labels", [])]

    if any(token in title for token in ("bug", "error", "fail", "failure", "crash", "broken")):
        value += 100
    if "critical" in labels:
        value += 150
    if "bug" in labels:
        value += 120
    if "security" in labels:
        value += 110
    if "ci" in labels or "test" in labels:
        value += 80
    if "enhancement" in labels:
        value += 10
    if "documentation" in labels or "docs" in labels:
        value += 5
    return value


def main():
    state = load_state()
    repo = state.get("ci", {}).get("repo_path") or state.get("github", {}).get("repo")
    if not repo:
        raise SystemExit("CI/GitHub repo path is not configured")

    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--limit",
        ISSUE_LIMIT,
        "--json",
        "number,title,labels,createdAt,url",
    ]
    issues = json.loads(subprocess.check_output(cmd, cwd=repo, text=True))
    ranked = sorted(issues, key=lambda item: (score(item), item.get("createdAt") or ""), reverse=True)
    selected = ranked[0] if ranked else None

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        github = state.setdefault("github", {})
        ai = state.setdefault("ai", {})
        ai["selected_issue_file"] = str(OUT)
        if selected:
            github["current_issue"] = selected.get("number")
            github["current_issue_title"] = selected.get("title")
            github["last_error"] = None
        else:
            github["current_issue"] = None
            github["current_issue_title"] = None
        github["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)

    print(json.dumps(selected, ensure_ascii=False))


if __name__ == "__main__":
    main()
