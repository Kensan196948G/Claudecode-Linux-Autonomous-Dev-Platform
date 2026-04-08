#!/usr/bin/env python3
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("CLUSTER_STATE_FILE", DEVOS_HOME / "cluster/controller/cluster_state.json"))
EVENTS = DEVOS_HOME / "cluster/events"
MIN_FREE_MB = float(os.environ.get("MIN_FREE_MB", "3000"))
MAX_CPU_PERCENT = float(os.environ.get("MAX_CPU_PERCENT", "85"))
DISK_ALERT_PERCENT = float(os.environ.get("DISK_ALERT_PERCENT", "90"))


def save_state(data):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE)


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    worker_map = {worker["id"]: worker for worker in state.get("workers", [])}

    for hb_file in EVENTS.glob("heartbeat-*.json"):
        hb = json.loads(hb_file.read_text(encoding="utf-8"))
        worker = worker_map.get(hb.get("worker_id"))
        if not worker:
            continue
        worker["last_heartbeat"] = hb["time"]
        worker["hostname"] = hb.get("hostname", worker.get("hostname"))
        worker["memory_free_mb"] = hb["memory_free_mb"]
        worker["cpu_percent"] = hb["cpu_percent"]
        worker["disk_used_percent"] = hb["disk_used_percent"]
        worker["max_jobs"] = hb.get("max_jobs", worker.get("max_jobs", 1))
        worker["tags"] = hb.get("tags", worker.get("tags", []))
        worker["status"] = "busy" if worker.get("current_jobs", 0) > 0 else "idle"
        if hb["memory_free_mb"] < MIN_FREE_MB or hb["cpu_percent"] > MAX_CPU_PERCENT or hb["disk_used_percent"] > DISK_ALERT_PERCENT:
            worker["drain"] = True
        elif worker.get("drain") == "auto":
            worker["drain"] = False

    save_state(state)


if __name__ == "__main__":
    main()
