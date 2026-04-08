#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
SUMMARY = DEVOS_HOME / "runtime/ci/last_failure_summary.txt"
OUT = DEVOS_HOME / "runtime/ci/repair_prompt.md"

state = json.loads(STATE.read_text(encoding="utf-8"))
summary = SUMMARY.read_text(encoding="utf-8") if SUMMARY.exists() else "No CI summary available."
decision = state.get("decision", {})
ci = state.get("ci", {})

content = f"""# CI Repair Prompt

## Time
{datetime.now():%Y-%m-%d %H:%M:%S}

## Mode
CI Repair

## Current State
- next_action: {decision.get('next_action')}
- current_mode: {decision.get('current_mode')}
- repair_attempt_count: {ci.get('repair_attempt_count')}
- repair_attempt_limit: {ci.get('repair_attempt_limit')}
- last_run_status: {ci.get('last_run_status')}
- last_failure_summary: {ci.get('last_failure_summary')}

## Instructions
1. Read the CI failure summary and narrow the likely causes to at most three.
2. Make the smallest safe repair.
3. Run focused local verification when available.
4. Update relevant Docs if behavior or operations change.
5. Create a repair commit only for relevant changes.
6. Do not perform unrelated refactors.
7. If memory pressure is high, split tests or use lighter checks.

## CI Failure Summary
{summary}
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(content, encoding="utf-8")
print(str(OUT))
