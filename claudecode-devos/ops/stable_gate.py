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
REQUIRED_SUCCESSES = int(os.environ.get("STABLE_REQUIRED_SUCCESSES", "3"))

SUCCESS_VALUES = {"success", "passed", "pass", "ok", "clean", "approved", "approve", "no issues"}


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE_FILE)


def normalized(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def ok(value):
    return normalized(value) in SUCCESS_VALUES


def evaluate_ci(ci):
    required = int(ci.get("required_stable_successes") or REQUIRED_SUCCESSES)
    ci["required_stable_successes"] = required

    checks = {
        "test success": ci.get("local_test_status"),
        "lint success": ci.get("lint_status"),
        "build success": ci.get("build_status"),
        "CI success": ci.get("last_run_status"),
        "review OK": ci.get("codex_review_status"),
        "security OK": ci.get("security_status"),
    }
    blockers = [f"{name}: {value or 'unknown'}" for name, value in checks.items() if not ok(value)]

    error_count = int(ci.get("error_count") or 0)
    if error_count != 0:
        blockers.append(f"error count is {error_count}")

    if blockers:
        ci["stable_success_count"] = 0
    else:
        ci["stable_success_count"] = int(ci.get("stable_success_count") or 0) + 1

    ci["stable_blockers"] = blockers
    ci["stable"] = not blockers and int(ci.get("stable_success_count") or 0) >= required
    ci["stable_last_evaluated_at"] = timestamp()
    return ci["stable"], blockers


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    if mode not in {"evaluate", "check"}:
        print("Usage: stable_gate.py [evaluate|check]", file=sys.stderr)
        return 2

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        ci = state.setdefault("ci", {})
        stable, blockers = evaluate_ci(ci)
        save_state(state)

    if stable:
        print("STABLE")
        return 0
    print("UNSTABLE")
    for blocker in blockers:
        print(f"- {blocker}")
    return 1 if mode == "check" else 0


if __name__ == "__main__":
    raise SystemExit(main())
