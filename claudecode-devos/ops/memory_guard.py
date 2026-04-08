#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
ENV_FILE = DEVOS_HOME / "config/devos.env"
LOG_FILE = DEVOS_HOME / "runtime/logs/memory-guard.log"
STATE_UPDATER = DEVOS_HOME / "ops/state_manager.py"
RECOVERY = DEVOS_HOME / "ops/recovery.sh"
NOTIFIER = DEVOS_HOME / "notifications/notifier.py"


def load_env():
    result = subprocess.run(
        ["bash", "-c", 'set -a; source "$1"; env -0', "bash", str(ENV_FILE)],
        check=True,
        capture_output=True,
    )
    env = {}
    for item in result.stdout.decode("utf-8").split("\0"):
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        env[key] = value
    return env


def log(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%F %T} {msg}\n")


def state_set(path, value):
    subprocess.run([str(STATE_UPDATER), "set", path, str(value)], check=False)


def main():
    env = load_env()

    min_free_mb = int(env.get("MIN_FREE_MB", "3000"))
    max_swap_mb = int(env.get("MAX_SWAP_USED_MB", "1000"))
    max_cpu_percent = float(env.get("MAX_CPU_PERCENT", "85"))
    max_loadavg = float(env.get("MAX_LOADAVG", "3.0"))
    disk_alert_percent = float(env.get("DISK_ALERT_PERCENT", "90"))

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)
    load1, _, _ = psutil.getloadavg()
    disk = psutil.disk_usage("/")

    free_mb = round(mem.available / 1024 / 1024, 2)
    swap_used_mb = round(swap.used / 1024 / 1024, 2)
    cpu_percent = round(cpu, 2)
    loadavg_1m = round(load1, 2)
    disk_percent = round(disk.percent, 2)

    log(f"[CHECK] free={free_mb:.2f}MB swap={swap_used_mb:.2f}MB cpu={cpu_percent:.2f}% load1={loadavg_1m:.2f} disk={disk_percent:.2f}%")

    state_set("resources.memory_free_mb", free_mb)
    state_set("resources.swap_used_mb", swap_used_mb)
    state_set("resources.cpu_percent", cpu_percent)
    state_set("resources.loadavg_1m", loadavg_1m)
    state_set("resources.disk_used_percent", disk_percent)

    recovery_reasons = []
    warning_reasons = []

    if free_mb < min_free_mb:
        recovery_reasons.append(f"free_mb<{min_free_mb}")
    if swap_used_mb > max_swap_mb:
        recovery_reasons.append(f"swap_used_mb>{max_swap_mb}")
    if cpu_percent > max_cpu_percent:
        warning_reasons.append(f"cpu>{max_cpu_percent}")
    if loadavg_1m > max_loadavg:
        warning_reasons.append(f"load1>{max_loadavg}")
    if disk_percent > disk_alert_percent:
        warning_reasons.append(f"disk>{disk_alert_percent}")

    if recovery_reasons:
        reasons = ",".join(recovery_reasons + warning_reasons)
        log(f"[ALERT] recovery triggered reasons={reasons}")
        state_set("system.status", "recovering")
        state_set("system.health", "warning")
        subprocess.run(
            [
                str(NOTIFIER),
                "RECOVERY",
                f"Memory issue detected. Free={free_mb}MB Swap={swap_used_mb}MB Reasons={reasons}",
            ],
            check=False,
        )
        subprocess.run([str(RECOVERY)], check=False)
    elif warning_reasons:
        log(f"[WARN] reasons={','.join(warning_reasons)}")
        state_set("system.status", "running")
        state_set("system.health", "warning")
    else:
        state_set("system.status", "running")
        state_set("system.health", "healthy")


if __name__ == "__main__":
    main()
