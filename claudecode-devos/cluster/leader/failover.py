#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
LEADER_FILE = DEVOS_HOME / "cluster/leader/leader.json"
CLUSTER_STATE = Path(os.environ.get("CLUSTER_STATE_FILE", DEVOS_HOME / "cluster/controller/cluster_state.json"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def candidates():
    if not CLUSTER_STATE.exists():
        return ["controller-A", "controller-B"]
    state = json.loads(CLUSTER_STATE.read_text(encoding="utf-8"))
    items = [item["id"] for item in state.get("controllers", []) if item.get("enabled")]
    return items or ["controller-A", "controller-B"]


def failover():
    options = candidates()
    current = None
    if LEADER_FILE.exists():
        current = json.loads(LEADER_FILE.read_text(encoding="utf-8")).get("leader")
    if current in options and len(options) > 1:
        next_index = (options.index(current) + 1) % len(options)
        new_leader = options[next_index]
    else:
        new_leader = options[0]
    write_json(
        LEADER_FILE,
        {
            "leader": new_leader,
            "failed_over_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "previous_leader": current,
            "method": "manual-file-failover",
        },
    )
    print(new_leader)
    return new_leader


if __name__ == "__main__":
    failover()
