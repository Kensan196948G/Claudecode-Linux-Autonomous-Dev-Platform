#!/usr/bin/env python3
import fcntl
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE_FILE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK_FILE = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def coerce_value(value):
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_state():
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"{STATE_FILE} not found")
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE_FILE)


def update_path(state, path, value):
    node = state
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    node[keys[-1]] = value


def get_path(state, path):
    node = state
    for key in path.split("."):
        node = node[key]
    return node


def with_lock(callback):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        result = callback(state)
        save_state(state)
        return result


def usage():
    print("Usage: state_manager.py set <path> <value> | touch <path> | inc <path> [amount] | get <path>")
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        usage()

    action = sys.argv[1]
    path = sys.argv[2]

    if action == "set":
        if len(sys.argv) < 4:
            print("Missing value")
            sys.exit(1)
        value = coerce_value(sys.argv[3])
        with_lock(lambda state: update_path(state, path, value))
    elif action == "touch":
        with_lock(lambda state: update_path(state, path, now()))
    elif action == "inc":
        amount = int(sys.argv[3]) if len(sys.argv) >= 4 else 1

        def inc(state):
            current = get_path(state, path)
            update_path(state, path, int(current or 0) + amount)

        with_lock(inc)
    elif action == "get":
        state = load_state()
        print(json.dumps(get_path(state, path), ensure_ascii=False))
    else:
        usage()


if __name__ == "__main__":
    main()
