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
goal = state.get("goal", {})
kpi = state.get("kpi", {})
claudeos_dir = DEVOS_HOME / "templates/claudeos"
claudeos_note = "available" if claudeos_dir.exists() else "missing"

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
- stable: {ci.get('stable')}
- stable_success_count: {ci.get('stable_success_count')}/{ci.get('required_stable_successes')}
- stable_blockers: {ci.get('stable_blockers')}
- goal: {goal.get('title')}
- kpi_status: {kpi.get('status')}
- kpi_success_rate: {kpi.get('current_success_rate')}/{kpi.get('success_rate_target')}
- ClaudeOS template: {claudeos_note}

## Instructions
1. `.claude/claudeos` が同期済みであることを前提に、CI Manager / Repair / Verify の規約を確認してください。
2. CI失敗サマリーを読み、原因候補を最大3つに絞ってください。
3. 最小で安全な修復だけを行ってください。
4. 利用可能なら焦点を絞ったローカル検証を実行してください。
5. 振る舞いまたは運用が変わる場合は、関連Docsを更新してください。
6. 関連する変更だけをcommitしてください。
7. 無関係なリファクタリングは禁止です。
8. メモリ圧迫がある場合は、テストを分割するか軽量な確認を優先してください。
9. STABLE未達のままmerge/deployしないでください。

## CI Failure Summary
{summary}
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(content, encoding="utf-8")
print(str(OUT))
