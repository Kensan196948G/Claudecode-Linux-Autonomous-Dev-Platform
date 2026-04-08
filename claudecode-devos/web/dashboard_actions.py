#!/usr/bin/env python3
import base64
import json
import os
import signal
import shlex
import shutil
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
DEVOS_ENV = DEVOS_HOME / "config/devos.env"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def config_env_value(name, default=""):
    if name in os.environ and os.environ[name]:
        return os.environ[name]
    if not DEVOS_ENV.exists():
        return default
    prefix = f"export {name}="
    for line in DEVOS_ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix):].strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        marker = f"${{{name}:-"
        if value.startswith(marker) and value.endswith("}"):
            return value[len(marker):-1]
        return value
    return default


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


def build_foreground_shell_script(name, command):
    quoted_command = " ".join(shlex.quote(part) for part in command)
    return "\n".join([
        "set -o pipefail",
        f"cd {shlex.quote(str(DEVOS_HOME))}",
        f"export DEVOS_HOME={shlex.quote(str(DEVOS_HOME))}",
        "export DEVOS_CLAUDE_FOREGROUND=true",
        f"echo '[DevOS] {name} を別ターミナルで開始します。'",
        "echo '[DevOS] Claude CLIの標準出力をこの端末へ表示します。'",
        quoted_command,
        "rc=$?",
        "echo",
        "echo \"[DevOS] 終了しました rc=$rc\"",
        "read -r -p '[DevOS] Enterで閉じます...' _",
        "exit \"$rc\"",
    ])


def powershell_single_quote(value):
    return "'" + value.replace("'", "''") + "'"


def powershell_encoded_command(script):
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def cmd_base64_command(command):
    return base64.b64encode(command.encode("utf-8")).decode("ascii")


def write_terminal_script(shell_script):
    script_path = DEVOS_HOME / "runtime/tmp/devos-terminal-launch.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(shell_script + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    return script_path


def windows_terminal_paths():
    candidates = [
        Path("/mnt/c/Users") / user / "AppData/Local/Microsoft/WindowsApps/wt.exe"
        for user in os.listdir("/mnt/c/Users")
    ] if Path("/mnt/c/Users").exists() else []
    candidates.extend([
        Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"),
        Path("/mnt/c/Windows/System32/cmd.exe"),
    ])
    return [path for path in candidates if path.exists()]


def terminal_launch_config():
    terminal_cmd = config_env_value("DEVOS_TERMINAL_CMD")
    if terminal_cmd:
        return {"kind": "linux", "command": terminal_cmd, "source": "DEVOS_TERMINAL_CMD"}

    windows_ssh_target = config_env_value("DEVOS_WINDOWS_TERMINAL_SSH_TARGET")
    linux_ssh_target = config_env_value("DEVOS_LINUX_SSH_TARGET")
    if windows_ssh_target and linux_ssh_target and shutil.which("ssh"):
        return {
            "kind": "windows_ssh",
            "windows_ssh_target": windows_ssh_target,
            "linux_ssh_target": linux_ssh_target,
            "source": "DEVOS_WINDOWS_TERMINAL_SSH_TARGET",
        }

    wt_path = shutil.which("wt.exe")
    if wt_path:
        return {"kind": "wsl", "command": wt_path, "source": "PATH wt.exe"}
    for path in windows_terminal_paths():
        if path.name == "wt.exe":
            return {"kind": "wsl", "command": str(path), "source": "WindowsApps wt.exe"}

    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return None
    for command in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal"):
        found = shutil.which(command)
        if found:
            return {"kind": "linux", "command": found, "source": command}
    return None


def preflight_windows_terminal(config):
    check_command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ConnectTimeout=5",
        config["windows_ssh_target"],
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "if (Get-Command wt.exe -ErrorAction SilentlyContinue) { 'WINDOWS_TERMINAL_OK' } else { exit 2 }",
    ]
    try:
        result = subprocess.run(
            check_command,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"Windows SSH timed out: {config['windows_ssh_target']}:22"
    except OSError as exc:
        return False, f"Windows SSH preflight failed: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, detail or f"Windows Terminal preflight failed rc={result.returncode}"
    return True, (result.stdout or "").strip()


def windows_task_terminal_command(config, shell_script):
    remote_script = write_terminal_script(shell_script)
    runner_content = (
        "[Console]::BackgroundColor = 'Black'\r\n"
        "[Console]::ForegroundColor = 'White'\r\n"
        "$Host.UI.RawUI.BackgroundColor = 'Black'\r\n"
        "$Host.UI.RawUI.ForegroundColor = 'White'\r\n"
        "Clear-Host\r\n"
        "Write-Host '[DevOS] PowerShell runner started.'\r\n"
        f"ssh -tt {config['linux_ssh_target']} bash {remote_script}\r\n"
        "Write-Host ''\r\n"
        "Read-Host '[DevOS] Press Enter to close'\r\n"
    )
    launcher_content = (
        "@echo off\r\n"
        "set RUNNER=%TEMP%\\devos-claude-runner.ps1\r\n"
        "start \"DevOS Claude\" powershell.exe -NoExit -ExecutionPolicy Bypass -File \"%RUNNER%\"\r\n"
    )
    runner_b64 = cmd_base64_command(runner_content)
    launcher_b64 = cmd_base64_command(launcher_content)
    ps_script = "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$taskName = 'DevOSClaudeLaunch'",
        "$cmdPath = Join-Path $env:TEMP 'devos-claude-launch.cmd'",
        "$runnerPath = Join-Path $env:TEMP 'devos-claude-runner.ps1'",
        f"[IO.File]::WriteAllBytes($runnerPath, [Convert]::FromBase64String('{runner_b64}'))",
        f"[IO.File]::WriteAllBytes($cmdPath, [Convert]::FromBase64String('{launcher_b64}'))",
        "schtasks.exe /Create /TN $taskName /SC ONCE /ST 23:59 /TR $cmdPath /F /IT | Write-Output",
        "schtasks.exe /Run /TN $taskName | Write-Output",
    ])
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        config["windows_ssh_target"],
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        powershell_encoded_command(ps_script),
    ]


def spawn_terminal_action(name, command):
    running = running_action()
    if running:
        return False, f"既に実行中のDashboardジョブがあります: pid={running}"
    config = terminal_launch_config()
    if not config:
        log("[ACTION] terminal launch skipped reason=no Windows SSH target, WSL terminal, graphical terminal, DISPLAY, or WAYLAND_DISPLAY")
        return spawn_action(name, command)

    if config["kind"] == "windows_ssh":
        ok, detail = preflight_windows_terminal(config)
        if not ok:
            log(f"[ACTION] terminal launch blocked reason={detail}")
            return False, f"Windowsターミナル起動に失敗しました: {detail}"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    UI_DIR.mkdir(parents=True, exist_ok=True)

    shell_script = build_foreground_shell_script(name, command)

    env = os.environ.copy()
    env["DEVOS_HOME"] = str(DEVOS_HOME)
    env["DEVOS_CLAUDE_FOREGROUND"] = "true"
    if config["kind"] == "windows_ssh":
        terminal_command = windows_task_terminal_command(config, shell_script)
    elif config["kind"] == "wsl":
        terminal_command = [config["command"], "new-tab", "bash", "-lc", shell_script]
    else:
        terminal_command = [config["command"], "-e", "/bin/bash", "-lc", shell_script]

    log(f"[ACTION] terminal launch attempt kind={config['kind']} source={config.get('source')} command={shlex.join(terminal_command)}")
    try:
        proc = subprocess.Popen(
            terminal_command,
            cwd=str(DEVOS_HOME),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        log(f"[ACTION] terminal launch failed error={exc}; falling back to background")
        return spawn_action(name, command)

    ACTION_PID.write_text(str(proc.pid), encoding="utf-8")
    log(f"[ACTION] terminal started name={name} pid={proc.pid} kind={config['kind']}")
    return True, f"{name} を別ターミナルで開始しました: pid={proc.pid}"


def run_develop():
    return spawn_terminal_action("開発実行", [str(DEVOS_HOME / "bin/run-scheduled-project.sh")])


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
