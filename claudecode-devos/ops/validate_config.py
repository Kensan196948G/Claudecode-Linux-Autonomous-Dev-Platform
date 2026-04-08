#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
PROJECTS = Path(os.environ.get("DEVOS_PROJECTS_FILE", DEVOS_HOME / "config/projects.json"))
CLUSTER_STATE = Path(os.environ.get("CLUSTER_STATE_FILE", DEVOS_HOME / "cluster/controller/cluster_state.json"))

REQUIRED_STATE_KEYS = {
    "system",
    "limits",
    "usage",
    "resources",
    "claude",
    "projects",
    "github",
    "decision",
    "ci",
    "risk",
    "scheduler",
    "projects_runtime",
    "dashboard",
    "control",
    "worktree",
    "history",
    "strategy",
}

VALID_NEXT_ACTIONS = {"idle", "develop", "verify", "repair_ci", "cooldown", "suspend"}
VALID_STRATEGY_MODES = {"balanced", "growth", "safe", "finish-fast"}


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid json: {path}: {exc}") from None


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_state(errors):
    state = load_json(STATE)
    missing = REQUIRED_STATE_KEYS - set(state)
    require(not missing, f"state missing top-level keys: {sorted(missing)}", errors)

    decision = state.get("decision", {})
    require(decision.get("next_action") in VALID_NEXT_ACTIONS, f"invalid decision.next_action: {decision.get('next_action')}", errors)

    ci = state.get("ci", {})
    repair_limit = ci.get("repair_attempt_limit")
    require(isinstance(repair_limit, int) and 1 <= repair_limit <= 15, f"ci.repair_attempt_limit must be 1..15: {repair_limit}", errors)
    require(ci.get("merge_policy") == "ci-green-only", f"ci.merge_policy must be ci-green-only: {ci.get('merge_policy')}", errors)
    required_stable_successes = ci.get("required_stable_successes", 3)
    require(isinstance(required_stable_successes, int) and 1 <= required_stable_successes <= 15, f"ci.required_stable_successes must be 1..15: {required_stable_successes}", errors)

    usage = state.get("usage", {})
    for key in ("daily_seconds_used", "daily_limit_seconds", "weekly_seconds_used", "weekly_limit_seconds"):
        require(isinstance(usage.get(key), int), f"usage.{key} must be integer", errors)
    require(usage.get("daily_limit_seconds", 0) > 0, "usage.daily_limit_seconds must be positive", errors)
    require(usage.get("weekly_limit_seconds", 0) > 0, "usage.weekly_limit_seconds must be positive", errors)

    strategy = state.get("strategy", {})
    require(strategy.get("mode") in VALID_STRATEGY_MODES, f"invalid strategy.mode: {strategy.get('mode')}", errors)
    weights = strategy.get("weights", {})
    require(isinstance(weights, dict) and weights, "strategy.weights must be non-empty object", errors)
    if isinstance(weights, dict) and weights:
        total_weight = sum(float(value) for value in weights.values())
        require(0.99 <= total_weight <= 1.01, f"strategy weights should sum to 1.0: {total_weight}", errors)

    control = state.get("control", {})
    require(isinstance(control.get("manual_override"), bool), "control.manual_override must be boolean", errors)

    goal = state.get("goal", {})
    require(isinstance(goal, dict) and bool(goal.get("title")), "goal.title must be defined", errors)
    kpi = state.get("kpi", {})
    target = kpi.get("success_rate_target")
    require(isinstance(target, (int, float)) and 0 < float(target) <= 1, f"kpi.success_rate_target must be 0..1: {target}", errors)
    execution = state.get("execution", {})
    require(execution.get("max_duration_minutes") == 300, f"execution.max_duration_minutes must be 300: {execution.get('max_duration_minutes')}", errors)
    automation = state.get("automation", {})
    require(isinstance(automation.get("auto_issue_generation"), bool), "automation.auto_issue_generation must be boolean", errors)
    return state


def validate_projects(errors):
    projects_data = load_json(PROJECTS)
    projects = projects_data.get("projects", [])
    require(isinstance(projects, list), "projects.projects must be a list", errors)
    seen = set()
    for project in projects:
        pid = project.get("id")
        require(pid, "project.id is required", errors)
        require(pid not in seen, f"duplicate project id: {pid}", errors)
        seen.add(pid)
        require(project.get("status") in {"active", "paused", "blocked", "done", "archived"}, f"invalid status for {pid}: {project.get('status')}", errors)
        require(project.get("priority") in {"high", "medium", "low"}, f"invalid priority for {pid}: {project.get('priority')}", errors)
        require(isinstance(project.get("weight"), int), f"project.weight must be integer for {pid}", errors)
        for field in ("estimated_value", "estimated_effort", "strategic_fit", "personal_interest", "maintenance_cost", "ci_stability", "current_progress", "blocker_risk", "expected_reuse"):
            value = project.get(field)
            require(isinstance(value, int) and 0 <= value <= 100, f"{pid}.{field} must be 0..100 integer: {value}", errors)


def validate_cluster(errors):
    if not CLUSTER_STATE.exists():
        return
    cluster = load_json(CLUSTER_STATE)
    worker_ids = set()
    for worker in cluster.get("workers", []):
        wid = worker.get("id")
        require(wid, "cluster worker id is required", errors)
        require(wid not in worker_ids, f"duplicate worker id: {wid}", errors)
        worker_ids.add(wid)
        require(isinstance(worker.get("enabled"), bool), f"worker.enabled must be boolean for {wid}", errors)
        require(isinstance(worker.get("drain"), bool), f"worker.drain must be boolean for {wid}", errors)
        require(isinstance(worker.get("max_jobs"), int) and worker.get("max_jobs") >= 1, f"worker.max_jobs must be positive integer for {wid}", errors)


def main():
    errors = []
    validate_state(errors)
    validate_projects(errors)
    validate_cluster(errors)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print("config validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
