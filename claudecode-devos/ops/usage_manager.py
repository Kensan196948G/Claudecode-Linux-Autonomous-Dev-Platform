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
DAILY_LIMIT_SECONDS = int(os.environ.get("SESSION_MAX_SECONDS", "18000"))
WEEKLY_LIMIT_SECONDS = int(os.environ.get("WEEKLY_LIMIT_SECONDS", "90000"))
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now():
    return datetime.now()


def timestamp(dt):
    return dt.strftime(TIME_FORMAT)


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE_FILE)


def ensure_usage(state):
    usage = state.setdefault("usage", {})
    usage.setdefault("daily_seconds_used", 0)
    usage.setdefault("daily_limit_seconds", DAILY_LIMIT_SECONDS)
    usage.setdefault("weekly_seconds_used", 0)
    usage.setdefault("weekly_limit_seconds", WEEKLY_LIMIT_SECONDS)
    usage.setdefault("last_reset_daily", None)
    usage.setdefault("last_reset_weekly", None)
    return usage


def parse_time(value):
    if not value:
        return None
    return datetime.strptime(value, TIME_FORMAT)


def apply_resets(state, current):
    usage = ensure_usage(state)
    last_daily = parse_time(usage.get("last_reset_daily"))
    if last_daily is None or last_daily.date() != current.date():
        usage["daily_seconds_used"] = 0
        usage["last_reset_daily"] = timestamp(current)

    last_weekly = parse_time(usage.get("last_reset_weekly"))
    should_reset_weekly = current.weekday() == 4 and current.hour == 13
    already_reset_this_hour = (
        last_weekly is not None
        and last_weekly.date() == current.date()
        and last_weekly.hour == current.hour
    )
    if should_reset_weekly and not already_reset_this_hour:
        usage["weekly_seconds_used"] = 0
        usage["last_reset_weekly"] = timestamp(current)


def with_lock(callback):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        result = callback(state)
        save_state(state)
        return result


def check_limits(state):
    usage = ensure_usage(state)
    daily_used = int(usage.get("daily_seconds_used") or 0)
    daily_limit = int(usage.get("daily_limit_seconds") or DAILY_LIMIT_SECONDS)
    weekly_used = int(usage.get("weekly_seconds_used") or 0)
    weekly_limit = int(usage.get("weekly_limit_seconds") or WEEKLY_LIMIT_SECONDS)

    if daily_used >= daily_limit:
        state.setdefault("system", {})["last_error"] = "daily usage limit reached"
        return 2, f"Daily limit reached: {daily_used}/{daily_limit}s"
    if weekly_used >= weekly_limit:
        state.setdefault("system", {})["last_error"] = "weekly usage limit reached"
        return 3, f"Weekly limit reached: {weekly_used}/{weekly_limit}s"
    return 0, f"Usage available: daily={daily_used}/{daily_limit}s weekly={weekly_used}/{weekly_limit}s"


def command_reset(state):
    apply_resets(state, now())
    return 0, "Usage reset check complete"


def command_check(state):
    apply_resets(state, now())
    return check_limits(state)


def command_record(state, seconds):
    apply_resets(state, now())
    usage = ensure_usage(state)
    duration = max(0, int(seconds))
    usage["daily_seconds_used"] = int(usage.get("daily_seconds_used") or 0) + duration
    usage["weekly_seconds_used"] = int(usage.get("weekly_seconds_used") or 0) + duration
    return check_limits(state)


def usage():
    print("Usage: usage_manager.py reset | check | record <seconds>", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        usage()

    action = sys.argv[1]
    if action == "reset":
        code, message = with_lock(command_reset)
    elif action == "check":
        code, message = with_lock(command_check)
    elif action == "record":
        if len(sys.argv) < 3:
            usage()
        code, message = with_lock(lambda state: command_record(state, sys.argv[2]))
    else:
        usage()

    print(message)
    sys.exit(code)


if __name__ == "__main__":
    main()
