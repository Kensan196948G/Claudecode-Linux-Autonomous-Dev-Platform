#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
LOCK = Path(os.environ.get("DEVOS_LOCK_DIR", DEVOS_HOME / "runtime/tmp")) / "state.lock"
ISSUE = DEVOS_HOME / "runtime/issues/selected_issue.json"
CI_SUMMARY = DEVOS_HOME / "runtime/ci/last_failure_summary.txt"
OUT = DEVOS_HOME / "runtime/prompts/current_prompt.md"
EVOLUTION_PROMPT = DEVOS_HOME / "runtime/prompts/evolution_instructions.md"
DOCS_DIR = DEVOS_HOME / "docs"
DOCS_MAX_BYTES = int(os.environ.get("PROMPT_DOCS_MAX_BYTES", "12000"))


def read_json(path):
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text or text == "null":
        return None
    return json.loads(text)


def docs_context():
    chunks = []
    total = 0
    if not DOCS_DIR.exists():
        return "No DevOS Docs directory found."
    for path in sorted(DOCS_DIR.rglob("*.md")):
        rel = path.relative_to(DOCS_DIR)
        text = path.read_text(encoding="utf-8", errors="ignore")
        snippet = f"\n## docs/{rel}\n{text}\n"
        if total + len(snippet.encode("utf-8")) > DOCS_MAX_BYTES:
            break
        chunks.append(snippet)
        total += len(snippet.encode("utf-8"))
    return "\n".join(chunks) if chunks else "No Docs context selected."


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    issue = read_json(ISSUE)
    ci_summary = CI_SUMMARY.read_text(encoding="utf-8") if CI_SUMMARY.exists() else "None"
    evolution_prompt = EVOLUTION_PROMPT.read_text(encoding="utf-8") if EVOLUTION_PROMPT.exists() else "No evolution instructions generated yet."
    decision = state.get("decision", {})
    ci = state.get("ci", {})
    resources = state.get("resources", {})
    usage = state.get("usage", {})

    prompt = f"""# Claude Auto Prompt

## Time
{datetime.now():%Y-%m-%d %H:%M:%S}

## Mode
{decision.get('next_action')}

## System State
- decision_reason: {decision.get('reason')}
- current_mode: {decision.get('current_mode')}
- memory_free_mb: {resources.get('memory_free_mb')}
- swap_used_mb: {resources.get('swap_used_mb')}
- cpu_percent: {resources.get('cpu_percent')}
- disk_used_percent: {resources.get('disk_used_percent')}
- ci_status: {ci.get('last_run_status')}
- repair_attempt_count: {ci.get('repair_attempt_count')}
- daily_seconds_used: {usage.get('daily_seconds_used')}
- weekly_seconds_used: {usage.get('weekly_seconds_used')}

## Current Issue
```json
{json.dumps(issue, ensure_ascii=False, indent=2)}
```

## CI Failure Summary
```text
{ci_summary}
```

## Docs Context
{docs_context()}

## Evolution Instructions
{evolution_prompt}

## Instructions
- Resolve the selected issue or the current CI failure, depending on Mode.
- Make the smallest safe change.
- Run focused tests or validation when available.
- Update relevant Docs when behavior or operations change.
- Commit only relevant changes.
- Do not push to the base branch directly.
- If resource pressure exists, prefer lightweight checks.
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(prompt, encoding="utf-8")

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text(encoding="utf-8"))
        ai = state.setdefault("ai", {})
        ai["current_prompt_file"] = str(OUT)
        ai["last_prompt_built_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(OUT))


if __name__ == "__main__":
    main()
