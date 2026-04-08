#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE_FILE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK_FILE = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
CLAUDE_HOME = Path(os.environ.get("DEVOS_CLAUDE_HOME", str(Path.home() / ".claude")))
QUALITY_TIMEOUT_SECONDS = int(os.environ.get("DEVOS_QUALITY_TIMEOUT_SECONDS", "900"))
GLOBAL_CLAUDEOS_SYNC = os.environ.get("DEVOS_GLOBAL_CLAUDEOS_SYNC", "false").lower() == "true"
AUTO_ISSUE_GENERATION = os.environ.get("GITHUB_AUTO_ISSUE_GENERATION", "false").lower() == "true"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE_FILE)


def with_state(callback):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        result = callback(state)
        save_state(state)
        return result


def run(cmd, cwd=None, timeout=60):
    try:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        class Result:
            returncode = 124 if isinstance(exc, subprocess.TimeoutExpired) else 127
            stdout = ""
            stderr = str(exc)

        return Result()


def repo_path(state, explicit=None):
    value = explicit or state.get("ci", {}).get("repo_path") or state.get("github", {}).get("repo")
    return Path(value).resolve() if value else None


def command_exists(name):
    return shutil.which(name) is not None


def detect_commands(repo):
    commands = {"test": [], "lint": [], "build": [], "security": []}
    package_json = repo / "package.json"
    if package_json.exists():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError:
            scripts = {}
        if "test" in scripts and command_exists("npm"):
            commands["test"].append(["npm", "test", "--", "--watch=false"])
        if "lint" in scripts and command_exists("npm"):
            commands["lint"].append(["npm", "run", "lint"])
        if "build" in scripts and command_exists("npm"):
            commands["build"].append(["npm", "run", "build"])
        if command_exists("npm"):
            commands["security"].append(["npm", "audit", "--audit-level=high"])
    has_python = (
        (repo / "pyproject.toml").exists()
        or (repo / "pytest.ini").exists()
        or (repo / "tests").exists()
        or any(repo.glob("**/*.py"))
    )
    if has_python:
        if command_exists("pytest"):
            commands["test"].append(["pytest", "-q"])
        if command_exists("ruff"):
            commands["lint"].append(["ruff", "check", "."])
        if command_exists("python3"):
            commands["build"].append([
                "python3",
                "-c",
                "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('.').rglob('*.py') if '.git' not in p.parts and '.claude' not in p.parts]",
            ])
        if command_exists("bandit"):
            commands["security"].append(["bandit", "-q", "-r", "."])
    if (repo / "go.mod").exists() and command_exists("go"):
        commands["test"].append(["go", "test", "./..."])
        commands["build"].append(["go", "build", "./..."])
    if (repo / "Cargo.toml").exists() and command_exists("cargo"):
        commands["test"].append(["cargo", "test", "--all"])
        commands["lint"].append(["cargo", "clippy", "--all-targets", "--", "-D", "warnings"])
        commands["build"].append(["cargo", "build", "--all"])
    if (repo / "pom.xml").exists() and command_exists("mvn"):
        commands["test"].append(["mvn", "test"])
        commands["build"].append(["mvn", "package", "-DskipTests"])
    return commands


def run_first(kind, commands, repo):
    if not commands:
        return "unknown", "no command detected"
    timeout = max(60, QUALITY_TIMEOUT_SECONDS // 4)
    for cmd in commands:
        proc = run(cmd, cwd=repo, timeout=timeout)
        detail = (proc.stdout + "\n" + proc.stderr).strip()[-2000:]
        if proc.returncode == 0:
            return "success", " ".join(cmd)
        if kind == "security" and proc.returncode in (0,):
            return "success", " ".join(cmd)
        return "failure", detail or "command failed: " + " ".join(cmd)
    return "unknown", "no command completed"


def update_quality(state, repo):
    ci = state.setdefault("ci", {})
    if not repo or not (repo / ".git").exists():
        ci["local_test_status"] = "unknown"
        ci["lint_status"] = "unknown"
        ci["build_status"] = "unknown"
        ci["security_status"] = "unknown"
        ci["last_quality_summary"] = "repo not available"
        return
    commands = detect_commands(repo)
    summaries = {}
    for kind, field in (
        ("test", "local_test_status"),
        ("lint", "lint_status"),
        ("build", "build_status"),
        ("security", "security_status"),
    ):
        status, detail = run_first(kind, commands[kind], repo)
        ci[field] = status
        summaries[kind] = {"status": status, "detail": detail}
    ci["last_quality_checked_at"] = timestamp()
    ci["last_quality_summary"] = summaries


def update_codex(state):
    codex = state.setdefault("codex", {})
    ci = state.setdefault("ci", {})
    exe = shutil.which("codex")
    codex["available"] = bool(exe)
    codex["last_checked_at"] = timestamp()
    if not exe:
        codex["setup_status"] = "missing"
        codex["review_status"] = "unknown"
        ci["codex_review_status"] = "unknown"
        return
    proc = run([exe, "--version"], timeout=10)
    codex["version"] = proc.stdout.strip() or proc.stderr.strip() or None
    codex["setup_status"] = "success" if proc.returncode == 0 else "failure"
    result_file = DEVOS_HOME / "runtime/codex/result.json"
    codex["last_result_file"] = str(result_file) if result_file.exists() else None
    if result_file.exists():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
            status = str(result.get("status") or result.get("review_status") or "unknown").lower()
        except json.JSONDecodeError:
            status = "failure"
    else:
        status = "unknown"
    codex["review_status"] = status
    ci["codex_review_status"] = "success" if status in {"success", "ok", "approved", "pass", "passed"} else status


def update_memory(state):
    memory = state.setdefault("memory", {})
    CLAUDE_HOME.mkdir(parents=True, exist_ok=True)
    global_state = CLAUDE_HOME / "state.json"
    claude_file = CLAUDE_HOME / "CLAUDE.md"
    claudeos_dir = CLAUDE_HOME / "claudeos"
    memory["claude_home"] = str(CLAUDE_HOME)
    memory["global_claude_file"] = str(claude_file)
    memory["global_state_file"] = str(global_state)
    memory["claudeos_dir"] = str(claudeos_dir)
    memory["last_checked_at"] = timestamp()
    global_state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    memory["last_saved_at"] = timestamp()
    if GLOBAL_CLAUDEOS_SYNC:
        src = DEVOS_HOME / "templates/claudeos"
        if src.exists():
            shutil.copytree(src, claudeos_dir, dirs_exist_ok=True)
            memory["last_claudeos_sync"] = timestamp()
    memory["status"] = "success" if global_state.exists() and claude_file.exists() else "partial"


CHAINS = {
    "Monitor": ["CTO", "ProductManager", "Analyst", "Architect", "DevOps"],
    "Development": ["Architect", "Developer", "Reviewer"],
    "Verify": ["QA", "Reviewer", "Security", "DevOps"],
    "Repair": ["Debugger", "Developer", "Reviewer", "QA", "DevOps"],
    "Improvement": ["EvolutionManager", "ProductManager", "Architect", "Developer", "QA"],
    "Release": ["ReleaseManager", "Reviewer", "Security", "DevOps", "CTO"],
}


def update_agent_teams(state, phase):
    teams = state.setdefault("agent_teams", {})
    chain = CHAINS.get(phase, CHAINS["Monitor"])
    teams["enabled"] = True
    teams["current_phase"] = phase
    teams["last_chain"] = chain
    teams["last_checked_at"] = timestamp()
    log = DEVOS_HOME / "runtime/agent_logs/agent_team_chain.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        for role in chain:
            f.write(f"{timestamp()} [{role}] 判断: phase={phase} status=registered\n")
    teams["last_log_status"] = "success"
    teams["last_log_file"] = str(log)


def update_github_projects(state, repo):
    gp = state.setdefault("github_projects", {})
    gp["last_checked_at"] = timestamp()
    if not command_exists("gh"):
        gp["enabled"] = False
        gp["status"] = "gh-missing"
        return
    if not repo or not (repo / ".git").exists():
        gp["status"] = "repo-missing"
        return
    owner = os.environ.get("GITHUB_PROJECT_OWNER", "")
    if not owner:
        owner_proc = run(["gh", "repo", "view", "--json", "owner", "--jq", ".owner.login"], cwd=repo, timeout=20)
        owner = owner_proc.stdout.strip() if owner_proc.returncode == 0 else ""
    if not owner:
        gp["enabled"] = False
        gp["status"] = "owner-unresolved"
        gp["last_error"] = "GITHUB_PROJECT_OWNER is not set and repo owner could not be resolved"
        return
    proc = run(["gh", "project", "list", "--owner", owner, "--format", "json"], cwd=repo, timeout=20)
    if proc.returncode == 0:
        gp["enabled"] = True
        gp["status"] = "available"
        gp["last_status"] = proc.stdout[:4000]
        gp["last_error"] = None
    else:
        gp["enabled"] = False
        gp["status"] = "unconfigured"
        gp["last_error"] = (proc.stderr or proc.stdout).strip()[:1000]


def update_time_tokens(state):
    usage = state.setdefault("usage", {})
    execution = state.setdefault("execution", {})
    tokens = state.setdefault("tokens", {})
    daily_used = int(usage.get("daily_seconds_used") or 0)
    daily_limit = int(usage.get("daily_limit_seconds") or os.environ.get("SESSION_MAX_SECONDS", "18000"))
    remaining = max(0, daily_limit - daily_used)
    execution["max_duration_minutes"] = daily_limit // 60
    execution["remaining_seconds"] = remaining
    if remaining < 300:
        phase = "stop-now"
    elif remaining < 900:
        phase = "verify-shrink"
    elif remaining < 1800:
        phase = "stop-improvement"
    else:
        phase = "normal"
    execution["time_phase"] = phase
    percent = round((daily_used / daily_limit) * 100, 2) if daily_limit else None
    tokens["usage_percent"] = percent
    tokens["last_checked_at"] = timestamp()
    if percent is None:
        tokens["status"] = "unknown"
    elif percent >= 95:
        tokens["status"] = "stop"
    elif percent >= 85:
        tokens["status"] = "verify-priority"
    elif percent >= 70:
        tokens["status"] = "improvement-stop"
    else:
        tokens["status"] = "normal"


def update_kpi(state):
    kpi = state.setdefault("kpi", {})
    ci = state.setdefault("ci", {})
    stable = bool(ci.get("stable"))
    blockers = ci.get("stable_blockers") or []
    current = 1.0 if stable else max(0.0, 1.0 - (len(blockers) * 0.15))
    target = float(kpi.get("success_rate_target") or 0.9)
    kpi["current_success_rate"] = round(min(1.0, current), 2)
    kpi["status"] = "met" if kpi["current_success_rate"] >= target else "unmet"
    kpi["last_evaluated_at"] = timestamp()
    state.setdefault("automation", {})["auto_issue_generation"] = AUTO_ISSUE_GENERATION


def main():
    parser = argparse.ArgumentParser(description="Run DevOS autonomous harness checks.")
    parser.add_argument("--repo")
    parser.add_argument("--phase", default="Monitor")
    parser.add_argument("--skip-quality", action="store_true")
    args = parser.parse_args()

    def apply(state):
        repo = repo_path(state, args.repo)
        if not args.skip_quality and os.environ.get("DEVOS_ENABLE_QUALITY_CHECKS", "true").lower() == "true":
            update_quality(state, repo)
        update_codex(state)
        update_memory(state)
        update_agent_teams(state, args.phase)
        update_github_projects(state, repo)
        update_time_tokens(state)
        update_kpi(state)

    with_state(apply)
    print("harness checks OK")


if __name__ == "__main__":
    main()
