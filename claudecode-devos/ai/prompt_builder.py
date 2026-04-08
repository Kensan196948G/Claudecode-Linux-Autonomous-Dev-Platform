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
ISSUE_FACTORY = DEVOS_HOME / "runtime/issues/factory_candidates.json"
OUT = DEVOS_HOME / "runtime/prompts/current_prompt.md"
EVOLUTION_PROMPT = DEVOS_HOME / "runtime/prompts/evolution_instructions.md"
SESSION_PROMPT_TEMPLATE = DEVOS_HOME / "templates/CLAUDEOS_SESSION_PROMPT.md"
CLAUDEOS_TEMPLATE_DIR = DEVOS_HOME / "templates/claudeos"
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


def session_prompt_template():
    if SESSION_PROMPT_TEMPLATE.exists():
        return SESSION_PROMPT_TEMPLATE.read_text(encoding="utf-8").strip()
    return "# ClaudeOS v7.1 セッション開始"


def claudeos_manifest():
    if not CLAUDEOS_TEMPLATE_DIR.exists():
        return "templates/claudeos is not available."
    paths = sorted(
        path.relative_to(CLAUDEOS_TEMPLATE_DIR).as_posix()
        for path in CLAUDEOS_TEMPLATE_DIR.rglob("*")
        if path.is_file()
    )
    return "\n".join(f"- `.claude/claudeos/{path}`" for path in paths)


def read_template_file(relative_path, fallback=""):
    path = CLAUDEOS_TEMPLATE_DIR / relative_path
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    return fallback


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    issue = read_json(ISSUE)
    issue_factory = read_json(ISSUE_FACTORY)
    ci_summary = CI_SUMMARY.read_text(encoding="utf-8") if CI_SUMMARY.exists() else "None"
    evolution_prompt = EVOLUTION_PROMPT.read_text(encoding="utf-8") if EVOLUTION_PROMPT.exists() else "No evolution instructions generated yet."
    decision = state.get("decision", {})
    ci = state.get("ci", {})
    resources = state.get("resources", {})
    usage = state.get("usage", {})
    goal = state.get("goal", {})
    kpi = state.get("kpi", {})
    execution = state.get("execution", {})
    automation = state.get("automation", {})
    codex = state.get("codex", {})
    memory = state.get("memory", {})
    agent_teams = state.get("agent_teams", {})
    github_projects = state.get("github_projects", {})
    tokens = state.get("tokens", {})
    claudeos_boot = read_template_file("system/boot.md")
    claudeos_orchestrator = read_template_file("system/orchestrator.md")
    claudeos_loop_guard = read_template_file("system/loop-guard.md")
    claudeos_token_budget = read_template_file("system/token-budget.md")

    prompt = f"""{session_prompt_template()}

## ClaudeOS テンプレート適用

このセッションは **完全自立型開発Claude** として実行します。
DevOS 起動時に `templates/claudeos` の全ファイルは対象リポジトリの `.claude/claudeos` へ同期されます。
以降の agents、skills、commands、rules、hooks、scripts、contexts、examples、mcp-configs、system、loops、ci、evolution、worktree 設定は `.claude/claudeos` を正規参照先として扱ってください。

### 起動時に必ず読む中核ファイル

1. `.claude/claudeos/system/boot.md`
2. `.claude/claudeos/system/orchestrator.md`
3. `.claude/claudeos/system/loop-guard.md`
4. `.claude/claudeos/system/token-budget.md`
5. `.claude/claudeos/loops/monitor-loop.md`
6. `.claude/claudeos/loops/build-loop.md`
7. `.claude/claudeos/loops/verify-loop.md`
8. `.claude/claudeos/loops/improve-loop.md`
9. `.claude/claudeos/ci/ci-manager.md`
10. `.claude/claudeos/evolution/self-evolution.md`

### 中核ファイル抜粋: system/boot.md

```md
{claudeos_boot}
```

### 中核ファイル抜粋: system/orchestrator.md

```md
{claudeos_orchestrator}
```

### 中核ファイル抜粋: system/loop-guard.md

```md
{claudeos_loop_guard}
```

### 中核ファイル抜粋: system/token-budget.md

```md
{claudeos_token_budget}
```

### ClaudeOS 全ファイル目録

{claudeos_manifest()}

## 24. 現在の実行コンテキスト

### 時刻
{datetime.now():%Y-%m-%d %H:%M:%S}

### モード
{decision.get('next_action')}

### Goal / KPI
- Goal: {goal.get('title')}
- Goal定義済み: {goal.get('defined')}
- KPI成功率: {kpi.get('current_success_rate')} / target={kpi.get('success_rate_target')}
- KPI状態: {kpi.get('status')}
- KPI最終評価: {kpi.get('last_evaluated_at')}

### システム状態
- 判定理由: {decision.get('reason')}
- 現在モード: {decision.get('current_mode')}
- 空きメモリMB: {resources.get('memory_free_mb')}
- swap使用MB: {resources.get('swap_used_mb')}
- CPU使用率: {resources.get('cpu_percent')}
- ディスク使用率: {resources.get('disk_used_percent')}
- CI状態: {ci.get('last_run_status')}
- 修復試行回数: {ci.get('repair_attempt_count')}
- 修復試行上限: {ci.get('repair_attempt_limit')}
- STABLE: {ci.get('stable')}
- STABLE連続成功回数: {ci.get('stable_success_count')}/{ci.get('required_stable_successes')}
- STABLE未達理由: {ci.get('stable_blockers')}
- test状態: {ci.get('local_test_status')}
- lint状態: {ci.get('lint_status')}
- build状態: {ci.get('build_status')}
- security状態: {ci.get('security_status')}
- Codex review状態: {ci.get('codex_review_status')}
- 本日使用秒数: {usage.get('daily_seconds_used')}
- 今週使用秒数: {usage.get('weekly_seconds_used')}
- 残り秒数: {execution.get('remaining_seconds')}
- 時間フェーズ: {execution.get('time_phase')}
- Token状態: {tokens.get('status')}
- Token使用率: {tokens.get('usage_percent')}
- Codex setup: {codex.get('setup_status')}
- Codex review: {codex.get('review_status')}
- Memory状態: {memory.get('status')}
- Memory保存先: {memory.get('global_state_file')}
- Agent Teamsフェーズ: {agent_teams.get('current_phase')}
- Agent Teamsチェーン: {agent_teams.get('last_chain')}
- GitHub Projects状態: {github_projects.get('status')}
- Issue自動生成: {automation.get('auto_issue_generation')}

### ハーネス制御
- 最大作業時間: {usage.get('daily_limit_seconds')}秒。5時間を超えて継続しないでください。
- Goal未定義の場合、大型変更を開始しないでください。
- KPI未達の場合、Issue Factory候補を確認し、P1/P2を優先してください。
- 時間フェーズが `stop-improvement` の場合はImprovementを停止してください。
- 時間フェーズが `verify-shrink` の場合はVerifyを縮退して終了準備を優先してください。
- 時間フェーズが `stop-now` の場合は新規作業を止め、終了処理へ移行してください。
- ループ登録完了後、通常開発前に `[ClaudeOS] LOOP_REGISTERED` を端末へ出力してください。
- `/codex:setup`、`/codex:status`、必要時の `/codex:review` 結果を確認し、結果を最終報告に含めてください。
- Memory MCP または利用可能なMemory相当の前回セッション情報を確認し、接続不可なら「Memory未接続」と明記してください。
- Agent Teamsを使った場合は、各ロールの判断ログを指定フォーマットで残してください。

### 現在のIssue
```json
{json.dumps(issue, ensure_ascii=False, indent=2)}
```

### Issue Factory候補
```json
{json.dumps(issue_factory, ensure_ascii=False, indent=2)}
```

### CI失敗サマリー
```text
{ci_summary}
```

### Docsコンテキスト
{docs_context()}

### Evolution指示
{evolution_prompt}

### 追加指示
- モードに応じて、選択されたIssueまたは現在のCI失敗を解決してください。
- 最小で安全な変更を優先してください。
- 利用可能なら、焦点を絞ったテストまたは検証を実行してください。
- 振る舞いまたは運用が変わる場合は、関連Docsを更新してください。
- 関連する変更だけをcommitしてください。
- base branchへ直接pushしないでください。
- STABLE未達のままmerge/deployしないでください。
- リソース圧迫がある場合は、軽量な確認を優先してください。
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
