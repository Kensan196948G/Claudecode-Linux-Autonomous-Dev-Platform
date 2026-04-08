#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
LOG = DEVOS_HOME / "runtime/logs/notifications.log"
SEND_ALERT = DEVOS_HOME / "ops/notify/send_alert.sh"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE)


def update_state(success, event_type, error=None):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        notifications = state.setdefault("notifications", {})
        notifications["last_event_type"] = event_type
        if success:
            notifications["last_sent"] = timestamp()
            notifications["last_error"] = None
        else:
            notifications["errors"] = int(notifications.get("errors") or 0) + 1
            notifications["last_error"] = error
        save_state(state)


def append_log(event_type, message, status):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp()} [{status}] {event_type}: {message}\n")


def notify_event(event_type, message):
    subject = f"[DevOS] {event_type}"
    body = f"{timestamp()}\n\n{message}"
    try:
        result = subprocess.run([str(SEND_ALERT), subject, body], check=False, text=True, capture_output=True)
        if result.returncode == 0:
            update_state(True, event_type)
            append_log(event_type, message, "SENT")
            return 0
        error = (result.stderr or result.stdout or f"send_alert rc={result.returncode}").strip()
        update_state(False, event_type, error)
        append_log(event_type, f"{message} error={error}", "ERROR")
        return result.returncode
    except Exception as exc:
        update_state(False, event_type, str(exc))
        append_log(event_type, f"{message} error={exc}", "ERROR")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Send DevOS notification events.")
    parser.add_argument("event_type")
    parser.add_argument("message", nargs="?", default="")
    args = parser.parse_args()
    return notify_event(args.event_type, args.message)


if __name__ == "__main__":
    sys.exit(main())
