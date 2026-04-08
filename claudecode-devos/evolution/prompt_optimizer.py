#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
PROMPT_FRAGMENT = Path(os.environ.get("DEVOS_EVOLUTION_PROMPT_FILE", DEVOS_HOME / "runtime/prompts/evolution_instructions.md"))


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


def build_fragment(state):
    evolution = state.get("evolution", {})
    mode = evolution.get("mode", "normal")
    strategy = evolution.get("task_strategy", "standard")
    lines = [
        "# Evolution Instructions",
        "",
        f"- Evolution mode: {mode}",
        f"- Task strategy: {strategy}",
    ]
    if mode == "safe":
        lines.extend(
            [
                "- Prefer smaller changes and focused verification.",
                "- Avoid broad refactors unless required to recover correctness.",
                "- Stop and document risk if repeated failures continue.",
            ]
        )
    elif mode == "aggressive":
        lines.extend(
            [
                "- Prefer direct implementation when tests and state are healthy.",
                "- Keep changes scoped, but reduce unnecessary exploration.",
                "- Still avoid pushing to the base branch directly.",
            ]
        )
    else:
        lines.append("- Follow the normal safe development policy.")

    if strategy == "split":
        lines.append("- Split slow tasks into smaller checkpoints before broad verification.")
    return "\n".join(lines) + "\n"


def evolve_prompt():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        content = build_fragment(state)
        PROMPT_FRAGMENT.parent.mkdir(parents=True, exist_ok=True)
        PROMPT_FRAGMENT.write_text(content, encoding="utf-8")
        evolution = state.setdefault("evolution", {})
        evolution["last_prompt_evolved_at"] = timestamp()
        evolution["prompt_fragment_file"] = str(PROMPT_FRAGMENT)
        save_state(state)
    print(PROMPT_FRAGMENT)
    return PROMPT_FRAGMENT


if __name__ == "__main__":
    evolve_prompt()
