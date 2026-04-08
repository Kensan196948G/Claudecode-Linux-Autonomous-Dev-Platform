#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
PROJECTS = Path(os.environ.get("DEVOS_PROJECTS_FILE", DEVOS_HOME / "config/projects.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
OUT = DEVOS_HOME / "runtime/projects/selected_project.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def days_until(date_str):
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        return (target.date() - datetime.now().date()).days
    except (TypeError, ValueError):
        return 9999


def score_project(project):
    if project.get("status") != "active":
        return -9999

    selection_status = project.get("selection_status", "candidate")
    if selection_status == "selected":
        strategy_score = 300
    elif selection_status == "candidate":
        strategy_score = 100
    elif selection_status == "hold":
        strategy_score = 20
    elif selection_status == "drop":
        return -9999
    else:
        strategy_score = 50

    priority_score = {"high": 100, "medium": 60, "low": 20}.get(project.get("priority", "low"), 0)
    score = strategy_score + priority_score + int(project.get("weight", 0) or 0)
    score += float(project.get("last_score", 0) or 0)

    due_days = days_until(project.get("release_due", "2099-12-31"))
    if due_days < 0:
        return -9999
    if due_days <= 14:
        score += 80
    elif due_days <= 30:
        score += 40
    elif due_days <= 60:
        score += 20

    if not project.get("last_run_at"):
        score += 20

    return score


def main():
    projects_data = load_json(PROJECTS)
    projects = projects_data.get("projects", [])
    ranked = sorted(projects, key=lambda item: (score_project(item), item.get("registered_at", "")), reverse=True)
    active_ranked = [project for project in ranked if project.get("status") == "active" and score_project(project) > 0]
    selected = active_ranked[0] if active_ranked else None

    state_snapshot = load_json(STATE)
    control = state_snapshot.get("control", {})
    manual_project_id = control.get("manual_project_id")
    if control.get("manual_override") and manual_project_id:
        manual_matches = [project for project in active_ranked if project.get("id") == manual_project_id]
        if manual_matches:
            selected = manual_matches[0]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    save_json(OUT, selected if selected else {})

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE)
        scheduler = state.setdefault("scheduler", {})
        runtime = state.setdefault("projects_runtime", {})
        projects_state = state.setdefault("projects", {})
        github = state.setdefault("github", {})
        ci = state.setdefault("ci", {})

        scheduler.setdefault("mode", "single")
        scheduler.setdefault("max_parallel_projects", 1)
        scheduler.setdefault("selection_policy", "weighted-priority")
        scheduler["last_schedule_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scheduler["last_selected_project"] = selected.get("id") if selected else None

        runtime["queued_projects"] = [project["id"] for project in active_ranked]
        runtime["active_projects"] = [selected["id"]] if selected else []
        runtime.setdefault("completed_today", [])
        runtime.setdefault("blocked_projects", [])

        if selected:
            projects_state["active_project"] = selected["id"]
            github["repo"] = selected.get("repository")
            ci["repo_path"] = selected.get("repository")
        projects_state["registered_count"] = len(projects)
        save_json(STATE, state)

    print(selected["id"] if selected else "NO_PROJECT")


if __name__ == "__main__":
    main()
