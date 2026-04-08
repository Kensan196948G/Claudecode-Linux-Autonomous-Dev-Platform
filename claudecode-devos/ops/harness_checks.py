#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
import re
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


def read_json_file(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def git_root(path):
    if not path:
        return None
    proc = run(["git", "rev-parse", "--show-toplevel"], cwd=path, timeout=10)
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return Path(path).resolve()


def workspace_slug(path):
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(path).name).strip("-")
    return slug or "workspace"


def workspace_hash(path):
    try:
        canonical = Path(path).resolve(strict=True)
    except OSError:
        canonical = Path(path).resolve()
    return hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()[:16]


def detect_codex_plugin():
    installed_file = CLAUDE_HOME / "plugins/installed_plugins.json"
    installed = read_json_file(installed_file, default={}) or {}
    installed = installed.get("plugins", installed) if isinstance(installed, dict) else {}
    for name in ("codex@openai-codex", "openai-codex/codex", "codex"):
        entries = installed.get(name)
        if isinstance(entries, list) and entries:
            install_path = entries[-1].get("installPath")
            if install_path:
                return name, Path(install_path)
    fallback = CLAUDE_HOME / "plugins/cache/openai-codex/codex/1.0.1"
    if fallback.exists():
        return "codex@openai-codex", fallback
    return None, None


def codex_plugin_state_candidates(workspace):
    slug = workspace_slug(workspace)
    digest = workspace_hash(workspace)
    state_name = f"{slug}-{digest}"
    roots = []
    for env_name in ("DEVOS_CODEX_PLUGIN_DATA", "CLAUDE_PLUGIN_DATA"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value) / "state")
    roots.append(CLAUDE_HOME / "plugins/data/codex-openai-codex/state")
    roots.append(Path("/tmp/codex-companion"))

    seen = set()
    for root in roots:
        state_dir = root / state_name
        if state_dir in seen:
            continue
        seen.add(state_dir)
        yield state_dir


def load_codex_job(state_dir, job):
    job_id = job.get("id")
    if not job_id:
        return job, None
    job_file = state_dir / "jobs" / f"{job_id}.json"
    payload = read_json_file(job_file)
    if isinstance(payload, dict):
        merged = {**job, **payload}
        return merged, job_file
    return job, job_file if job_file.exists() else None


def is_codex_review_job(job):
    text = " ".join(
        str(job.get(key) or "")
        for key in ("id", "jobClass", "kind", "kindLabel", "title", "reviewLabel", "phase")
    ).lower()
    if "review" in text or "adversarial" in text:
        return True
    result = job.get("result")
    if isinstance(result, dict):
        inner = result.get("result")
        return isinstance(inner, dict) and "findings" in inner and "verdict" in inner
    return False


def classify_codex_review(job):
    status = str(job.get("status") or "unknown").lower()
    result = job.get("result")
    verdict = None
    summary = None
    findings = []
    next_steps = []
    parse_error = None

    if isinstance(result, dict):
        parse_error = result.get("parseError") or result.get("parse_error")
        structured = result.get("result") if isinstance(result.get("result"), dict) else result
        verdict = structured.get("verdict") if isinstance(structured, dict) else None
        summary = structured.get("summary") if isinstance(structured, dict) else None
        findings = structured.get("findings") if isinstance(structured, dict) else []
        next_steps = structured.get("next_steps") if isinstance(structured, dict) else []
    elif isinstance(result, str):
        summary = result[:4000]

    findings = findings if isinstance(findings, list) else []
    next_steps = next_steps if isinstance(next_steps, list) else []
    normalized_verdict = str(verdict or "").strip().lower()
    blocking_findings = [
        item for item in findings
        if str(item.get("severity", "low")).lower() in {"critical", "high", "medium", "blocker"}
    ] if all(isinstance(item, dict) for item in findings) else findings

    if status in {"queued", "running"}:
        review_status = status
    elif status in {"failed", "failure", "cancelled", "canceled"} or parse_error:
        review_status = "failure"
    elif status == "completed":
        if blocking_findings:
            review_status = "failure"
        elif normalized_verdict in {"approved", "approve", "ok", "pass", "passed", "success", "clean", "no issues"}:
            review_status = "success"
        elif findings:
            review_status = "failure"
        else:
            review_status = "success"
    else:
        review_status = "unknown"

    return {
        "review_status": review_status,
        "ci_status": "success" if review_status == "success" else review_status,
        "verdict": verdict,
        "summary": summary,
        "findings": findings,
        "next_steps": next_steps,
        "parse_error": parse_error,
    }


def import_codex_plugin_result(repo):
    plugin_name, plugin_root = detect_codex_plugin()
    workspace = git_root(repo) if repo else None
    result = {
        "generated_at": timestamp(),
        "source": "codex-plugin-cc",
        "plugin_name": plugin_name,
        "plugin_installed": bool(plugin_root and plugin_root.exists()),
        "plugin_root": str(plugin_root) if plugin_root else None,
        "workspace": str(workspace) if workspace else None,
        "review_status": "unknown",
        "ci_status": "unknown",
        "reason": None,
    }
    if not plugin_root or not plugin_root.exists():
        result["reason"] = "codex-plugin-cc is not installed"
        return result
    if not workspace:
        result["reason"] = "workspace is not available"
        return result

    for state_dir in codex_plugin_state_candidates(workspace):
        state_file = state_dir / "state.json"
        plugin_state = read_json_file(state_file)
        if not isinstance(plugin_state, dict):
            continue
        jobs = [job for job in plugin_state.get("jobs", []) if isinstance(job, dict)]
        review_jobs = []
        for job in jobs:
            merged, job_file = load_codex_job(state_dir, job)
            if is_codex_review_job(merged):
                review_jobs.append((merged, job_file))
        review_jobs.sort(key=lambda item: str(item[0].get("updatedAt") or item[0].get("createdAt") or ""), reverse=True)
        result["plugin_state_file"] = str(state_file)
        result["plugin_state_dir"] = str(state_dir)
        if not review_jobs:
            result["reason"] = "no codex-plugin-cc review job found"
            return result
        job, job_file = review_jobs[0]
        normalized = classify_codex_review(job)
        result.update(normalized)
        result.update({
            "job_id": job.get("id"),
            "job_status": job.get("status"),
            "job_class": job.get("jobClass"),
            "job_kind": job.get("kindLabel") or job.get("kind"),
            "job_title": job.get("title"),
            "job_updated_at": job.get("updatedAt"),
            "job_file": str(job_file) if job_file else None,
            "reason": None,
        })
        return result

    result["reason"] = "codex-plugin-cc state file not found for workspace"
    return result


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


def update_codex(state, repo=None):
    codex = state.setdefault("codex", {})
    ci = state.setdefault("ci", {})
    exe = shutil.which("codex")
    codex["available"] = bool(exe)
    codex["last_checked_at"] = timestamp()
    plugin_result = import_codex_plugin_result(repo)
    result_file = DEVOS_HOME / "runtime/codex/result.json"
    existing_result = read_json_file(result_file)
    if (
        str(plugin_result.get("review_status") or "unknown").lower() == "unknown"
        and isinstance(existing_result, dict)
        and str(existing_result.get("review_status") or existing_result.get("status") or "unknown").lower() != "unknown"
        and (not existing_result.get("workspace") or existing_result.get("workspace") == plugin_result.get("workspace"))
    ):
        plugin_result = {
            **existing_result,
            "source": existing_result.get("source") or "runtime-codex-result-json",
            "review_status": existing_result.get("review_status") or existing_result.get("status"),
            "ci_status": existing_result.get("ci_status") or existing_result.get("review_status") or existing_result.get("status"),
            "fallback_reason": plugin_result.get("reason"),
        }
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(plugin_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    codex["plugin"] = plugin_result.get("plugin_name")
    codex["plugin_installed"] = plugin_result.get("plugin_installed")
    codex["plugin_root"] = plugin_result.get("plugin_root")
    codex["plugin_state_file"] = plugin_result.get("plugin_state_file")
    codex["plugin_job_id"] = plugin_result.get("job_id")
    codex["plugin_job_status"] = plugin_result.get("job_status")
    codex["last_result_file"] = str(result_file)
    codex["last_result_source"] = plugin_result.get("source")

    if not exe and not plugin_result.get("plugin_installed"):
        codex["setup_status"] = "missing"
        codex["review_status"] = "unknown"
        ci["codex_review_status"] = "unknown"
        return

    if exe:
        proc = run([exe, "--version"], timeout=10)
        codex["version"] = proc.stdout.strip() or proc.stderr.strip() or None
        cli_ok = proc.returncode == 0
    else:
        cli_ok = False
        codex["version"] = None
    codex["setup_status"] = "success" if (cli_ok or plugin_result.get("plugin_installed")) else "failure"

    status = str(plugin_result.get("review_status") or "unknown").lower()
    codex["review_status"] = status
    codex["review_verdict"] = plugin_result.get("verdict")
    codex["review_summary"] = plugin_result.get("summary")
    codex["review_reason"] = plugin_result.get("reason")
    ci["codex_review_status"] = plugin_result.get("ci_status") or ("success" if status in {"success", "ok", "approved", "pass", "passed"} else status)


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
        update_codex(state, repo)
        update_memory(state)
        update_agent_teams(state, args.phase)
        update_github_projects(state, repo)
        update_time_tokens(state)
        update_kpi(state)

    with_state(apply)
    print("harness checks OK")


if __name__ == "__main__":
    main()
