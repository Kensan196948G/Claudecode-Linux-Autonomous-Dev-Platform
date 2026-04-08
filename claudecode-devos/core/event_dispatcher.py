#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
sys.path.insert(0, str(DEVOS_HOME))

from notifications.notifier import notify_event  # noqa: E402


def on_error(error_msg):
    return notify_event("ERROR", error_msg)


def on_success(task):
    return notify_event("SUCCESS", f"{task} completed")


def on_daily_limit():
    return notify_event("LIMIT", "Daily limit reached")


def on_weekly_reset():
    return notify_event("RESET", "Weekly reset executed")


def main():
    parser = argparse.ArgumentParser(description="Dispatch DevOS lifecycle events.")
    parser.add_argument("event", choices=["error", "success", "daily_limit", "weekly_reset"])
    parser.add_argument("message", nargs="?", default="")
    args = parser.parse_args()

    if args.event == "error":
        return on_error(args.message or "Unknown error")
    if args.event == "success":
        return on_success(args.message or "Task")
    if args.event == "daily_limit":
        return on_daily_limit()
    if args.event == "weekly_reset":
        return on_weekly_reset()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
