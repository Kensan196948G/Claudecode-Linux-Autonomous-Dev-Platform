#!/usr/bin/env python3
import json
import os
import socket
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
LEADER_FILE = DEVOS_HOME / "cluster/leader/leader.json"
CLUSTER_STATE = Path(os.environ.get("CLUSTER_STATE_FILE", DEVOS_HOME / "cluster/controller/cluster_state.json"))
CONTROLLER_ID = os.environ.get("CLUSTER_CONTROLLER_ID") or socket.gethostname()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def elect():
    if LEADER_FILE.exists():
        data = json.loads(LEADER_FILE.read_text(encoding="utf-8"))
        return data["leader"]

    leader = CONTROLLER_ID
    if CLUSTER_STATE.exists():
        state = json.loads(CLUSTER_STATE.read_text(encoding="utf-8"))
        enabled = [item["id"] for item in state.get("controllers", []) if item.get("enabled")]
        if CONTROLLER_ID in enabled:
            leader = CONTROLLER_ID
        elif not enabled:
            leader = CONTROLLER_ID

    write_json(
        LEADER_FILE,
        {
            "leader": leader,
            "elected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "file",
        },
    )
    return leader


if __name__ == "__main__":
    print(elect())
