#!/usr/bin/env python3
import fcntl
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
sys.path.insert(0, str(DEVOS_HOME))

from evolution.metrics.analyzer import analyze  # noqa: E402

STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(data):
    with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, STATE)


def optimize():
    metrics = analyze()
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        evolution = state.setdefault("evolution", {})
        decision = {}

        fail_threshold = float(evolution.get("fail_rate_threshold", 0.3))
        success_threshold = float(evolution.get("success_rate_threshold", 0.8))
        slow_threshold = float(evolution.get("slow_avg_time_seconds", 60))

        if metrics["fail_rate"] > fail_threshold:
            evolution["mode"] = "safe"
            state.setdefault("system", {})["mode"] = "safe"
            decision["mode"] = "safe"
        elif metrics["success_rate"] > success_threshold and metrics["total"] >= 5:
            evolution["mode"] = "aggressive"
            state.setdefault("system", {})["mode"] = "aggressive"
            decision["mode"] = "aggressive"
        else:
            evolution["mode"] = evolution.get("mode", "normal")
            decision["mode"] = evolution["mode"]

        if metrics["avg_time"] > slow_threshold:
            evolution["task_strategy"] = "split"
            decision["task_strategy"] = "split"
        else:
            evolution["task_strategy"] = "standard"
            decision["task_strategy"] = "standard"

        evolution["last_metrics"] = metrics
        evolution["last_decision"] = decision
        evolution["last_optimized_at"] = timestamp()

        entry = {
            "time": evolution["last_optimized_at"],
            "type": "optimization",
            "metrics": metrics,
            "decision": decision,
        }
        state.setdefault("ai_decision_log", []).append(entry)
        state["ai_decision_log"] = state["ai_decision_log"][-50:]
        state.setdefault("ai", {}).setdefault("decision_log", []).append(entry)
        state["ai"]["decision_log"] = state["ai"]["decision_log"][-50:]
        save_state(state)
        return decision


if __name__ == "__main__":
    print(json.dumps(optimize(), ensure_ascii=False, indent=2))
