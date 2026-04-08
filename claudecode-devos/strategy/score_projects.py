#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
PROJECTS = Path(os.environ.get("DEVOS_PROJECTS_FILE", DEVOS_HOME / "config/projects.json"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
OUT = Path(os.environ.get("STRATEGY_SCORES_FILE", DEVOS_HOME / "strategy/scores/latest_scores.json"))

DEFAULT_WEIGHTS = {
    "roi": 0.30,
    "strategic_fit": 0.20,
    "urgency": 0.15,
    "reuse": 0.15,
    "stability": 0.10,
    "interest": 0.10,
}


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def calc_roi_score(project):
    value = float(project.get("estimated_value", 50) or 50)
    effort = max(1, float(project.get("estimated_effort", 50) or 50))
    maintenance = float(project.get("maintenance_cost", 20) or 20)
    reuse = float(project.get("expected_reuse", 50) or 50)
    raw = ((value * 0.6) + (reuse * 0.4) - (maintenance * 0.3)) / effort * 100
    return clamp(round(raw, 2))


def calc_urgency_score(project):
    due = project.get("release_due")
    if not due:
        return 30
    try:
        target = datetime.strptime(due, "%Y-%m-%d")
        days = (target.date() - datetime.now().date()).days
    except (TypeError, ValueError):
        return 30
    if days <= 7:
        return 100
    if days <= 14:
        return 85
    if days <= 30:
        return 70
    if days <= 60:
        return 50
    return 25


def calc_stability_score(project):
    ci = float(project.get("ci_stability", 50) or 50)
    blocker = float(project.get("blocker_risk", 30) or 30)
    return clamp(round(ci * 0.7 + (100 - blocker) * 0.3, 2))


def calc_value_score(project):
    strategic_fit = float(project.get("strategic_fit", 50) or 50)
    interest = float(project.get("personal_interest", 50) or 50)
    reuse = float(project.get("expected_reuse", 50) or 50)
    estimated_value = float(project.get("estimated_value", 50) or 50)
    return clamp(round(estimated_value * 0.35 + strategic_fit * 0.30 + reuse * 0.20 + interest * 0.15, 2))


def weighted_total(project, weights):
    roi = calc_roi_score(project)
    urgency = calc_urgency_score(project)
    stability = calc_stability_score(project)
    value_score = calc_value_score(project)
    total = (
        roi * weights["roi"]
        + float(project.get("strategic_fit", 50) or 50) * weights["strategic_fit"]
        + urgency * weights["urgency"]
        + float(project.get("expected_reuse", 50) or 50) * weights["reuse"]
        + stability * weights["stability"]
        + float(project.get("personal_interest", 50) or 50) * weights["interest"]
    )
    return {
        "project_id": project["id"],
        "name_ja": project.get("name_ja"),
        "roi_score": round(roi, 2),
        "urgency_score": round(urgency, 2),
        "stability_score": round(stability, 2),
        "value_score": round(value_score, 2),
        "total_score": round(total, 2),
    }


def main():
    projects_data = load_json(PROJECTS)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE)
        strategy = state.setdefault("strategy", {})
        weights = strategy.get("weights", DEFAULT_WEIGHTS)

        scored = []
        for project in projects_data.get("projects", []):
            if project.get("status") != "active":
                continue
            result = weighted_total(project, weights)
            scored.append(result)
            project["last_score"] = result["total_score"]

        scored.sort(key=lambda item: item["total_score"], reverse=True)
        generated_at = timestamp()
        strategy["last_scored_at"] = generated_at
        strategy["current_top_project"] = scored[0]["project_id"] if scored else None
        strategy["selection_reason"] = "highest weighted strategic score" if scored else None

        save_json(PROJECTS, projects_data)
        save_json(STATE, state)
        save_json(OUT, {"generated_at": generated_at, "weights": weights, "scores": scored})

    print(json.dumps(scored[:5], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
