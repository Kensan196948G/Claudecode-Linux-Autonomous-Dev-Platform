#!/usr/bin/env python3
import json
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOG_DIR = DEVOS_HOME / "runtime/logs"
PID_DIR = DEVOS_HOME / "runtime/pids"
UI_DIR = DEVOS_HOME / "runtime/ui_actions"
ACTION_PID = PID_DIR / "dashboard-action.pid"
ACTION_LOG = LOG_DIR / "dashboard-actions.log"
PROJECTS_ROOT = Path(os.environ.get("DEVOS_PROJECTS_ROOT", "/home/kensan/Projects"))


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def log(message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with ACTION_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp()} {message}\n")


def pid_is_running(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


def running_action():
    if not ACTION_PID.exists():
        return None
    pid = ACTION_PID.read_text(encoding="utf-8").strip()
    if pid and pid_is_running(pid):
        return pid
    ACTION_PID.unlink(missing_ok=True)
    return None


def spawn_action(name, command):
    running = running_action()
    if running:
        return False, f"既に実行中のDashboardジョブがあります: pid={running}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    UI_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DEVOS_HOME"] = str(DEVOS_HOME)
    with ACTION_LOG.open("a", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            command,
            cwd=str(DEVOS_HOME),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    ACTION_PID.write_text(str(proc.pid), encoding="utf-8")
    log(f"[ACTION] started name={name} pid={proc.pid} command={' '.join(command)}")
    return True, f"{name} を開始しました: pid={proc.pid}"


def run_develop():
    return spawn_action("開発実行", [str(DEVOS_HOME / "bin/run-scheduled-project.sh")])


def run_repair_ci():
    return spawn_action(
        "CI修復",
        [
            "/bin/bash",
            "-lc",
            f"{DEVOS_HOME}/ci/fetch_ci_failure.sh || true; {DEVOS_HOME}/ci/repair_ci_worktree.sh || true",
        ],
    )


def stop_claude():
    stopped = []
    for pid_file in [PID_DIR / "claude.pid", ACTION_PID]:
        if not pid_file.exists():
            continue
        pid = pid_file.read_text(encoding="utf-8").strip()
        if not pid:
            continue
        try:
            pid_int = int(pid)
            try:
                os.killpg(pid_int, signal.SIGTERM)
            except ProcessLookupError:
                os.kill(pid_int, signal.SIGTERM)
            stopped.append(pid)
        except ProcessLookupError:
            pass
        except ValueError:
            pass
    log(f"[ACTION] suspend requested stopped_pids={stopped}")
    return True, "停止を要求しました" if stopped else "停止状態にしました"


def discover_project_repositories(root=PROJECTS_ROOT):
    repos = []
    if not root.exists():
        return repos
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if (child / ".git").exists():
            repos.append({
                "id": child.name,
                "name": child.name,
                "repository": str(child),
                "docs_dir": str(child / "Docs"),
                "session_prompt_file": str(child / "START_PROMPT.md"),
            })
    return repos
