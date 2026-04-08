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
SESSION_PROMPT_TEMPLATE = DEVOS_HOME / "templates/CLAUDEOS_SESSION_PROMPT.md"
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


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    issue = read_json(ISSUE)
    ci_summary = CI_SUMMARY.read_text(encoding="utf-8") if CI_SUMMARY.exists() else "None"
    evolution_prompt = EVOLUTION_PROMPT.read_text(encoding="utf-8") if EVOLUTION_PROMPT.exists() else "No evolution instructions generated yet."
    decision = state.get("decision", {})
    ci = state.get("ci", {})
    resources = state.get("resources", {})
    usage = state.get("usage", {})

    prompt = f"""{session_prompt_template()}

## 24. 現在の実行コンテキスト

### 時刻
{datetime.now():%Y-%m-%d %H:%M:%S}

### モード
{decision.get('next_action')}

### システム状態
- 判定理由: {decision.get('reason')}
- 現在モード: {decision.get('current_mode')}
- 空きメモリMB: {resources.get('memory_free_mb')}
- swap使用MB: {resources.get('swap_used_mb')}
- CPU使用率: {resources.get('cpu_percent')}
- ディスク使用率: {resources.get('disk_used_percent')}
- CI状態: {ci.get('last_run_status')}
- 修復試行回数: {ci.get('repair_attempt_count')}
- 本日使用秒数: {usage.get('daily_seconds_used')}
- 今週使用秒数: {usage.get('weekly_seconds_used')}

### 現在のIssue
```json
{json.dumps(issue, ensure_ascii=False, indent=2)}
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
