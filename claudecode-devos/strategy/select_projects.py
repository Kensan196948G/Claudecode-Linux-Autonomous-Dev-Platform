#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
PROJECTS = Path(os.environ.get("DEVOS_PROJECTS_FILE", DEVOS_HOME / "config/projects.json"))
SCORES = Path(os.environ.get("STRATEGY_SCORES_FILE", DEVOS_HOME / "strategy/scores/latest_scores.json"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
HISTORY = Path(os.environ.get("STRATEGY_HISTORY_FILE", DEVOS_HOME / "strategy/history/selection_history.json"))


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {} if default is None else default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def main():
    scores_data = load_json(SCORES, {"scores": []})
    ranked = sorted(scores_data.get("scores", []), key=lambda item: item["total_score"], reverse=True)
    selected_ids = {ranked[0]["project_id"]} if ranked else set()
    scores = {item["project_id"]: item for item in ranked}

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        projects_data = load_json(PROJECTS, {"projects": []})
        state = load_json(STATE, {})

        for project in projects_data.get("projects", []):
            score = scores.get(project["id"], {}).get("total_score", 0)
            if project["id"] in selected_ids:
                project["selection_status"] = "selected"
            elif score >= 70:
                project["selection_status"] = "candidate"
            elif score >= 45:
                project["selection_status"] = "hold"
            else:
                project["selection_status"] = "drop"

        dropped = [project["id"] for project in projects_data.get("projects", []) if project.get("selection_status") == "drop"]
        strategy = state.setdefault("strategy", {})
        strategy["last_dropped_projects"] = dropped

        history = load_json(HISTORY, [])
        entry = {
            "time": timestamp(),
            "selected": [project["id"] for project in projects_data.get("projects", []) if project.get("selection_status") == "selected"],
            "candidate": [project["id"] for project in projects_data.get("projects", []) if project.get("selection_status") == "candidate"],
            "hold": [project["id"] for project in projects_data.get("projects", []) if project.get("selection_status") == "hold"],
            "drop": dropped,
        }
        history.append(entry)

        save_json(PROJECTS, projects_data)
        save_json(STATE, state)
        save_json(HISTORY, history[-50:])

    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
