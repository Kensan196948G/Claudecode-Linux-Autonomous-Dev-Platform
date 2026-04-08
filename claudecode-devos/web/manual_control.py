#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from re import sub

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


def select_project(project_id, reason="selected from dashboard", start_develop=False):
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
        control["manual_action"] = "develop" if start_develop else None
        control["manual_project_id"] = project_id
        control["manual_reason"] = reason
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        state.setdefault("scheduler", {})["last_selected_project"] = project_id
        state.setdefault("projects_runtime", {})["active_projects"] = [project_id]
        state.setdefault("projects", {})["active_project"] = project_id
        append_manual_history(state, "select_project", reason)
        write_json(STATE, state)


def project_id_from_path(repo_path):
    repo = Path(repo_path).resolve()
    raw = repo.name
    slug = sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
    return slug or "project"


def select_project_path(repo_path, reason="selected from dashboard"):
    repo = Path(repo_path).expanduser().resolve()
    projects_root = Path(os.environ.get("DEVOS_PROJECTS_ROOT", "/home/kensan/Projects")).resolve()
    try:
        repo.relative_to(projects_root)
    except ValueError as exc:
        raise ValueError(f"Project must be under {projects_root}: {repo}") from exc
    if not repo.is_dir() or not (repo / ".git").exists():
        raise ValueError(f"Project repository not found: {repo}")

    project_id = project_id_from_path(repo)
    projects_data = load_json(PROJECTS, {"projects": []})
    projects = projects_data.setdefault("projects", [])
    now = timestamp().split(" ")[0]
    release_due = (datetime.now() + timedelta(days=int(os.environ.get("PROJECT_TERM_DAYS", "183")))).strftime("%Y-%m-%d")
    found = None
    for project in projects:
        if project.get("repository") == str(repo) or project.get("id") == project_id:
            found = project
            break

    if found is None:
        found = {
            "id": project_id,
            "name_ja": repo.name,
            "name_en": repo.name,
            "repository": str(repo),
            "docs_dir": str(repo / "Docs"),
            "session_prompt_file": str(repo / "START_PROMPT.md"),
            "priority": "medium",
            "weight": 70,
            "status": "active",
            "category": "discovered",
            "registered_at": now,
            "release_due": release_due,
            "last_run_at": None,
            "last_result": None,
            "estimated_value": 60,
            "estimated_effort": 50,
            "strategic_fit": 60,
            "personal_interest": 60,
            "maintenance_cost": 30,
            "ci_stability": 50,
            "current_progress": 0,
            "blocker_risk": 30,
            "expected_reuse": 50,
            "last_score": None,
            "selection_status": "selected",
        }
        projects.append(found)
    else:
        found["repository"] = str(repo)
        found["docs_dir"] = str(repo / "Docs")
        found["session_prompt_file"] = str(repo / "START_PROMPT.md")
        found["status"] = "active"
        found["selection_status"] = "selected"

    for project in projects:
        if project is not found and project.get("selection_status") == "selected":
            project["selection_status"] = "candidate"

    write_json(PROJECTS, projects_data)
    write_json(SELECTED, found)

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE, {})
        control = state.setdefault("control", {})
        control["manual_override"] = True
        control["manual_action"] = None
        control["manual_project_id"] = found["id"]
        control["manual_reason"] = reason
        control["manual_requested_at"] = timestamp()
        control["manual_requested_by"] = "local-dashboard"
        state.setdefault("scheduler", {})["last_selected_project"] = found["id"]
        state.setdefault("projects_runtime", {})["active_projects"] = [found["id"]]
        state.setdefault("projects", {})["active_project"] = found["id"]
        state.setdefault("github", {})["repo"] = str(repo)
        state.setdefault("ci", {})["repo_path"] = str(repo)
        state["projects"]["registered_count"] = len(projects)
        append_manual_history(state, "select_project", f"{reason}: {repo}")
        write_json(STATE, state)
    return found


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
