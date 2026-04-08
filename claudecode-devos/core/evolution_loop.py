#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import time
import uuid
import fcntl
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
sys.path.insert(0, str(DEVOS_HOME))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"

from evolution.log_collector import collect_log  # noqa: E402
from evolution.optimizer.optimizer import optimize  # noqa: E402
from evolution.prompt_optimizer import evolve_prompt  # noqa: E402


EVOLUTION_HISTORY = DEVOS_HOME / "runtime/evolution/history"


def _sha256(text):
    return hashlib.sha256(str(text).encode()).hexdigest()


def record_evolution_fragment(detail, result):
    """Persist an evolution fragment to runtime/evolution/history/ for later review."""
    EVOLUTION_HISTORY.mkdir(parents=True, exist_ok=True)
    cycle_id = str(uuid.uuid4())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fragment = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cycle_id": cycle_id,
        "source": "evolution_loop",
        "result": result,
        "decision": detail.get("decision"),
        "prompt_fragment": str(detail.get("prompt_fragment", "")),
        "before_hash": _sha256(detail.get("prompt_fragment", "")),
        "after_hash": None,
        "approved": None,
        "approved_by": None,
        "approved_at": None,
    }
    frag_file = EVOLUTION_HISTORY / f"frag_{ts}_{cycle_id[:8]}.json"
    frag_file.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return frag_file


def mark_cycle(detail):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text(encoding="utf-8"))
        evolution = state.setdefault("evolution", {})
        evolution["last_cycle_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        evolution["last_cycle_detail"] = detail
        with NamedTemporaryFile("w", encoding="utf-8", dir=STATE.parent, delete=False) as tmp:
            json.dump(state, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_name = tmp.name
        os.replace(tmp_name, STATE)


def run_evolution_cycle():
    start = time.time()
    result = "success"
    detail = {}
    try:
        decision = optimize()
        fragment = evolve_prompt()
        detail = {"decision": decision, "prompt_fragment": str(fragment)}
        mark_cycle(detail)
    except Exception as exc:
        result = "failure"
        detail = {"error": str(exc)}
        raise
    finally:
        duration = time.time() - start
        collect_log("evolution_cycle", result, duration, detail)
        record_evolution_fragment(detail, result)
    return detail


if __name__ == "__main__":
    print(json.dumps(run_evolution_cycle(), ensure_ascii=False, indent=2))
