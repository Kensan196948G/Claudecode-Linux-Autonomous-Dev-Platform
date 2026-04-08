#!/usr/bin/env python3
import fcntl
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"

MODES = {
    "balanced": {"roi": 0.30, "strategic_fit": 0.20, "urgency": 0.15, "reuse": 0.15, "stability": 0.10, "interest": 0.10},
    "growth": {"roi": 0.25, "strategic_fit": 0.20, "urgency": 0.10, "reuse": 0.20, "stability": 0.05, "interest": 0.20},
    "safe": {"roi": 0.20, "strategic_fit": 0.15, "urgency": 0.15, "reuse": 0.10, "stability": 0.30, "interest": 0.10},
    "finish-fast": {"roi": 0.20, "strategic_fit": 0.15, "urgency": 0.30, "reuse": 0.10, "stability": 0.15, "interest": 0.10},
}


def save_state(state):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODES:
        print("Usage: apply_strategy_mode.py <balanced|growth|safe|finish-fast>", file=sys.stderr)
        return 1

    mode = sys.argv[1]
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text(encoding="utf-8"))
        strategy = state.setdefault("strategy", {})
        strategy["mode"] = mode
        strategy["weights"] = MODES[mode]
        save_state(state)
    print(f"Applied strategy mode: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
