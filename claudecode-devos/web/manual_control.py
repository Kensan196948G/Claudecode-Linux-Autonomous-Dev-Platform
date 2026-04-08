#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
PROJECTS = Path(os.environ.get("DEVOS_PROJECTS_FILE", DEVOS_HOME / "config/projects.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
SELECTED = DEVOS_HOME / "runtime/projects/selected_project.json"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_manual_history(state, action, reason):
    history = state.setdefault("history", {}).setdefault("last_manual_actions", [])
    history.append({"time": state["control"]["manual_requested_at"], "action": action, "reason": reason})
    state["history"]["last_manual_actions"] = history[-20:]


def set_manual_action(action, reason="dashboard"):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE, {})
        control = state.setdefault("control", {})
        control["manual_override"] = True
        control["manual_action"] = action
        control["manual_reason"] = reason
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        append_manual_history(state, action, reason)
        write_json(STATE, state)


def clear_manual_action(reason="resume from dashboard"):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE, {})
        control = state.setdefault("control", {})
        control["manual_override"] = False
        control["manual_action"] = None
        control["manual_reason"] = reason
        control["manual_project_id"] = None
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        append_manual_history(state, "resume", reason)
        write_json(STATE, state)


def select_project(project_id, reason="selected from dashboard"):
    projects = load_json(PROJECTS, {"projects": []}).get("projects", [])
    matches = [project for project in projects if project.get("id") == project_id]
    if not matches:
        raise ValueError(f"Unknown project id: {project_id}")
    project = matches[0]
    write_json(SELECTED, project)

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE, {})
        control = state.setdefault("control", {})
        control["manual_override"] = True
        control["manual_action"] = "develop"
        control["manual_project_id"] = project_id
        control["manual_reason"] = reason
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        state.setdefault("scheduler", {})["last_selected_project"] = project_id
        state.setdefault("projects_runtime", {})["active_projects"] = [project_id]
        state.setdefault("projects", {})["active_project"] = project_id
        append_manual_history(state, "select_project", reason)
        write_json(STATE, state)


def update_project(project_id, priority, status, weight):
    allowed_priorities = {"high", "medium", "low"}
    allowed_statuses = {"active", "paused", "blocked", "done", "archived"}
    if priority not in allowed_priorities:
        raise ValueError(f"Invalid priority: {priority}")
    if status not in allowed_statuses:
        raise ValueError(f"Invalid status: {status}")
    try:
        weight_value = int(weight)
    except ValueError as exc:
        raise ValueError(f"Invalid weight: {weight}") from exc

    projects_data = load_json(PROJECTS, {"projects": []})
    found = False
    for project in projects_data.get("projects", []):
        if project.get("id") == project_id:
            project["priority"] = priority
            project["status"] = status
            project["weight"] = weight_value
            found = True
            break
    if not found:
        raise ValueError(f"Unknown project id: {project_id}")

    write_json(PROJECTS, projects_data)

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE, {})
        state.setdefault("projects", {})["registered_count"] = len(projects_data.get("projects", []))
        control = state.setdefault("control", {})
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        append_manual_history(state, "update_project", f"{project_id} priority={priority} status={status} weight={weight_value}")
        write_json(STATE, state)
