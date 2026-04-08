#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path

import psutil

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
OUT_DIR = Path(os.environ.get("DEVOS_METRICS_DIR", DEVOS_HOME / "runtime/metrics"))
STATE_UPDATER = DEVOS_HOME / "ops/state_manager.py"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_state(*args):
    import subprocess

    subprocess.run([str(STATE_UPDATER), *args], check=False)


def main():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)
    load1, load5, load15 = psutil.getloadavg()
    disk = psutil.disk_usage("/")

    snapshot = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "memory_free_mb": round(mem.available / 1024 / 1024, 2),
        "swap_used_mb": round(swap.used / 1024 / 1024, 2),
        "cpu_percent": round(cpu, 2),
        "loadavg_1m": round(load1, 2),
        "loadavg_5m": round(load5, 2),
        "loadavg_15m": round(load15, 2),
        "disk_used_percent": round(disk.percent, 2),
    }

    run_state("set", "resources.memory_free_mb", str(snapshot["memory_free_mb"]))
    run_state("set", "resources.swap_used_mb", str(snapshot["swap_used_mb"]))
    run_state("set", "resources.cpu_percent", str(snapshot["cpu_percent"]))
    run_state("set", "resources.loadavg_1m", str(snapshot["loadavg_1m"]))
    run_state("set", "resources.disk_used_percent", str(snapshot["disk_used_percent"]))

    out_file = OUT_DIR / f"metrics-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
