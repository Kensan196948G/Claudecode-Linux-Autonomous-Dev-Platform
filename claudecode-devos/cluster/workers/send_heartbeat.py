#!/usr/bin/env python3
import json
import os
import shutil
import socket
from datetime import datetime
from pathlib import Path

import psutil

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
WORKER_CFG = Path(os.environ.get("CLUSTER_WORKER_CONFIG", DEVOS_HOME / "cluster/workers/worker_config.json"))
OUTBOX = DEVOS_HOME / "cluster/events"


def main():
    cfg = json.loads(WORKER_CFG.read_text(encoding="utf-8"))
    worker = cfg["worker"]

    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = shutil.disk_usage("/")

    payload = {
        "worker_id": worker["id"],
        "hostname": socket.gethostname(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "memory_free_mb": round(mem.available / 1024 / 1024, 2),
        "cpu_percent": round(cpu, 2),
        "disk_used_percent": round(((disk.total - disk.free) / disk.total) * 100, 2),
        "status": "healthy",
        "max_jobs": worker.get("max_jobs", 1),
        "tags": worker.get("tags", []),
    }

    OUTBOX.mkdir(parents=True, exist_ok=True)
    outfile = OUTBOX / f"heartbeat-{worker['id']}.json"
    outfile.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(outfile)


if __name__ == "__main__":
    main()
