#!/usr/bin/env python3
import argparse
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
REPORT_DIR = Path(os.environ.get("DEVOS_REPORT_DIR", DEVOS_HOME / "reports"))


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def file_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_state(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE)


def bullets(items, limit=10):
    if not items:
        return "- None"
    lines = []
    for item in items[-limit:]:
        if isinstance(item, dict):
            lines.append("- " + ", ".join(f"{k}={v}" for k, v in item.items()))
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def render_report(state, projects):
    usage = state.get("usage", {})
    resources = state.get("resources", {})
    decision = state.get("decision", {})
    ci = state.get("ci", {})
    scheduler = state.get("scheduler", {})
    history = state.get("history", {})
    evolution = state.get("evolution", {})
    goal = state.get("goal", {})
    kpi = state.get("kpi", {})
    execution = state.get("execution", {})
    automation = state.get("automation", {})
    codex = state.get("codex", {})
    memory = state.get("memory", {})
    agent_teams = state.get("agent_teams", {})
    github_projects = state.get("github_projects", {})
    tokens = state.get("tokens", {})
    ai_decisions = state.get("ai_decision_log") or state.get("ai", {}).get("decision_log", [])

    project_lines = []
    for project in projects.get("projects", []):
        project_lines.append(
            "\n".join(
                [
                    f"### {project.get('id')} - {project.get('name_ja') or project.get('name_en')}",
                    f"- status: {project.get('status')}",
                    f"- priority: {project.get('priority')}",
                    f"- weight: {project.get('weight')}",
                    f"- release_due: {project.get('release_due')}",
                    f"- last_run_at: {project.get('last_run_at')}",
                ]
            )
        )

    return f"""# ClaudeCode DevOS Report

## Time
{timestamp()}

## Decision
- next_action: {decision.get('next_action')}
- current_mode: {decision.get('current_mode')}
- reason: {decision.get('reason')}

## Goal / KPI
- goal: {goal.get('title')}
- goal_defined: {goal.get('defined')}
- kpi_status: {kpi.get('status')}
- success_rate: {kpi.get('current_success_rate')}/{kpi.get('success_rate_target')}
- auto_issue_generation: {automation.get('auto_issue_generation')}
- self_evolution: {automation.get('self_evolution')}

## Usage
- daily_hours: {round((usage.get('daily_seconds_used') or 0) / 3600, 2)}
- daily_limit_hours: {round((usage.get('daily_limit_seconds') or 0) / 3600, 2)}
- weekly_hours: {round((usage.get('weekly_seconds_used') or 0) / 3600, 2)}
- weekly_limit_hours: {round((usage.get('weekly_limit_seconds') or 0) / 3600, 2)}
- remaining_seconds: {execution.get('remaining_seconds')}
- time_phase: {execution.get('time_phase')}
- token_status: {tokens.get('status')}
- token_usage_percent: {tokens.get('usage_percent')}

## Resources
- memory_free_mb: {resources.get('memory_free_mb')}
- swap_used_mb: {resources.get('swap_used_mb')}
- cpu_percent: {resources.get('cpu_percent')}
- disk_used_percent: {resources.get('disk_used_percent')}
- loadavg_1m: {resources.get('loadavg_1m')}

## CI
- last_run_status: {ci.get('last_run_status')}
- last_run_id: {ci.get('last_run_id')}
- repair_attempt_count: {ci.get('repair_attempt_count')}
- repair_attempt_limit: {ci.get('repair_attempt_limit')}
- stable: {ci.get('stable')}
- stable_success_count: {ci.get('stable_success_count')}/{ci.get('required_stable_successes')}
- stable_blockers: {ci.get('stable_blockers')}
- local_test_status: {ci.get('local_test_status')}
- lint_status: {ci.get('lint_status')}
- build_status: {ci.get('build_status')}
- security_status: {ci.get('security_status')}
- codex_review_status: {ci.get('codex_review_status')}
- last_failure_summary: {ci.get('last_failure_summary')}

## Harness
- codex_setup_status: {codex.get('setup_status')}
- codex_review_status: {codex.get('review_status')}
- memory_status: {memory.get('status')}
- memory_state_file: {memory.get('global_state_file')}
- agent_phase: {agent_teams.get('current_phase')}
- agent_chain: {agent_teams.get('last_chain')}
- github_projects_status: {github_projects.get('status')}

## Scheduler
- mode: {scheduler.get('mode')}
- last_selected_project: {scheduler.get('last_selected_project')}
- last_schedule_at: {scheduler.get('last_schedule_at')}

## Evolution
- mode: {evolution.get('mode')}
- task_strategy: {evolution.get('task_strategy')}
- last_cycle_at: {evolution.get('last_cycle_at')}
- last_optimized_at: {evolution.get('last_optimized_at')}
- last_metrics: {json.dumps(evolution.get('last_metrics'), ensure_ascii=False)}

## Recent AI Decision Log
{bullets(ai_decisions, limit=5)}

## Recent Project Runs
{bullets(history.get('last_project_runs', []), limit=10)}

## Recent CI Repairs
{bullets(history.get('last_ci_repairs', []), limit=10)}

## Projects
{chr(10).join(project_lines) if project_lines else 'No projects registered.'}
"""


def generate_report():
    state = load_json(STATE, {})
    projects = load_json(PROJECTS, {"projects": []})
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"report_{file_stamp()}.md"
    report_path.write_text(render_report(state, projects), encoding="utf-8")

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        locked_state = load_json(STATE, {})
        reports = locked_state.setdefault("reports", {})
        reports["last_generated_at"] = timestamp()
        reports["last_report_file"] = str(report_path)
        save_state(locked_state)

    print(report_path)
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Generate a DevOS markdown report.")
    parser.parse_args()
    generate_report()


if __name__ == "__main__":
    main()
