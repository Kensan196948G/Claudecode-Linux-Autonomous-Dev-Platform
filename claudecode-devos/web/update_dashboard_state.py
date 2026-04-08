#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"

LOCK.parent.mkdir(parents=True, exist_ok=True)
with LOCK.open("w", encoding="utf-8") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    data = json.loads(STATE.read_text(encoding="utf-8"))
    dashboard = data.setdefault("dashboard", {})
    dashboard["last_refresh_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
