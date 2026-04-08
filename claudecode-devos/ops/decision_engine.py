#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE_FILE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK_FILE = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
DECISION_LOG = DEVOS_HOME / "runtime/decisions/decision.log"
MIN_FREE_MB = float(os.environ.get("MIN_FREE_MB", "3000"))
MAX_SWAP_USED_MB = float(os.environ.get("MAX_SWAP_USED_MB", "1000"))
MAX_CPU_PERCENT = float(os.environ.get("MAX_CPU_PERCENT", "85"))
DISK_ALERT_PERCENT = float(os.environ.get("DISK_ALERT_PERCENT", "90"))
COOLDOWN_SECONDS = int(os.environ.get("DECISION_COOLDOWN_SECONDS", "900"))
REPAIR_LIMIT = int(os.environ.get("CI_REPAIR_ATTEMPT_LIMIT", "15"))


def now():
    return datetime.now()


def timestamp(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE_FILE)


def log(message):
    DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DECISION_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp(now())} {message}\n")


def ensure_sections(state):
    state.setdefault("goal", {
        "title": "自律開発最適化",
        "description": "ClaudeOS v7.1 完全無人運用版として、Goal Drivenな自律開発を安全に継続する",
        "defined": True,
    })
    state.setdefault("kpi", {
        "success_rate_target": 0.9,
        "current_success_rate": None,
        "status": "unknown",
        "last_evaluated_at": None,
    })
    state.setdefault("execution", {
        "max_duration_minutes": 300,
        "remaining_seconds": 0,
        "time_phase": "unknown",
    })
    state.setdefault("automation", {
        "auto_issue_generation": False,
        "self_evolution": True,
        "issue_factory_last_run_at": None,
    })
    state.setdefault("codex", {
        "available": None,
        "version": None,
        "setup_status": "unknown",
        "review_status": "unknown",
        "last_checked_at": None,
        "last_result_file": None,
    })
    state.setdefault("memory", {
        "claude_home": None,
        "global_claude_file": None,
        "global_state_file": None,
        "claudeos_dir": None,
        "status": "unknown",
        "last_checked_at": None,
        "last_saved_at": None,
    })
    state.setdefault("agent_teams", {
        "enabled": True,
        "current_phase": "Monitor",
        "last_chain": [],
        "last_log_status": "unknown",
        "last_checked_at": None,
    })
    state.setdefault("github_projects", {
        "enabled": False,
        "status": "unconfigured",
        "last_status": None,
        "last_checked_at": None,
        "last_error": None,
    })
    state.setdefault("tokens", {
        "status": "unknown",
        "budget": {
            "Monitor": 10,
            "Development": 35,
            "Verify": 20,
            "Improvement": 10,
            "Debug": 15,
            "IssueFactory": 5,
            "Release": 5,
        },
        "usage_percent": None,
        "last_checked_at": None,
    })

    decision = state.setdefault("decision", {})
    decision.setdefault("current_mode", "safe")
    decision.setdefault("next_action", "idle")
    decision.setdefault("reason", None)
    decision.setdefault("cooldown_until", None)
    decision.setdefault("last_decision_at", None)

    ci = state.setdefault("ci", {})
    ci.setdefault("enabled", True)
    ci.setdefault("repo_path", None)
    ci.setdefault("default_branch", "main")
    ci.setdefault("last_checked_at", None)
    ci.setdefault("last_run_status", None)
    ci.setdefault("last_run_id", None)
    ci.setdefault("last_failure_summary", None)
    ci.setdefault("repair_attempt_count", 0)
    ci.setdefault("repair_attempt_limit", REPAIR_LIMIT)
    ci.setdefault("last_repair_at", None)
    ci.setdefault("auto_merge_enabled", False)
    ci.setdefault("merge_policy", "ci-green-only")
    ci.setdefault("stable", False)
    ci.setdefault("stable_success_count", 0)
    ci.setdefault("required_stable_successes", int(os.environ.get("STABLE_REQUIRED_SUCCESSES", "3")))
    ci.setdefault("stable_blockers", ["not evaluated"])
    ci.setdefault("local_test_status", None)
    ci.setdefault("lint_status", None)
    ci.setdefault("build_status", None)
    ci.setdefault("security_status", None)
    ci.setdefault("codex_review_status", None)
    ci.setdefault("error_count", 0)

    risk = state.setdefault("risk", {})
    risk.setdefault("memory_pressure", False)
    risk.setdefault("cpu_pressure", False)
    risk.setdefault("disk_pressure", False)
    risk.setdefault("ci_unstable", False)
    return decision, ci, risk


def decide(state):
    current = now()
    decision, ci, risk = ensure_sections(state)
    resources = state.get("resources", {})

    mem_free = resources.get("memory_free_mb")
    swap_used = resources.get("swap_used_mb")
    cpu = resources.get("cpu_percent")
    disk = resources.get("disk_used_percent")
    ci_status = ci.get("last_run_status")
    repair_attempts = int(ci.get("repair_attempt_count") or 0)
    repair_limit = int(ci.get("repair_attempt_limit") or REPAIR_LIMIT)

    memory_pressure = (mem_free is not None and float(mem_free) < MIN_FREE_MB) or (
        swap_used is not None and float(swap_used) > MAX_SWAP_USED_MB
    )
    cpu_pressure = cpu is not None and float(cpu) > MAX_CPU_PERCENT
    disk_pressure = disk is not None and float(disk) > DISK_ALERT_PERCENT
    ci_unstable = ci_status in {"failure", "timed_out", "startup_failure", "action_required"}

    risk["memory_pressure"] = memory_pressure
    risk["cpu_pressure"] = cpu_pressure
    risk["disk_pressure"] = disk_pressure
    risk["ci_unstable"] = ci_unstable

    next_action = "develop"
    reason = "normal development"
    cooldown_until = None

    if disk_pressure:
        next_action = "suspend"
        reason = "disk pressure"
    elif memory_pressure or cpu_pressure:
        next_action = "cooldown"
        reason = "resource pressure"
        cooldown_until = timestamp(current + timedelta(seconds=COOLDOWN_SECONDS))
    elif ci.get("enabled", True) and ci_unstable and repair_attempts < repair_limit:
        next_action = "repair_ci"
        reason = "ci failed"
    elif ci.get("enabled", True) and ci_unstable and repair_attempts >= repair_limit:
        next_action = "suspend"
        reason = "repair attempts exceeded"

    decision["current_mode"] = "safe" if (memory_pressure or cpu_pressure) else "normal"
    decision["next_action"] = next_action
    decision["reason"] = reason
    decision["cooldown_until"] = cooldown_until
    decision["last_decision_at"] = timestamp(current)
    return next_action, reason, decision["current_mode"]


def main():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        next_action, reason, mode = decide(state)
        save_state(state)
    log(f"[DECISION] next_action={next_action} mode={mode} reason={reason}")
    print(next_action)


if __name__ == "__main__":
    main()
