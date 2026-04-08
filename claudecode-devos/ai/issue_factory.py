#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("DEVOS_STATE_FILE", DEVOS_HOME / "config/state.json"))
OUT = DEVOS_HOME / "runtime/issues/factory_candidates.json"
AUTO_CREATE_ENV = os.environ.get("GITHUB_AUTO_ISSUE_GENERATION", "false").lower() == "true"
CREATE_LIMIT = int(os.environ.get("ISSUE_FACTORY_CREATE_LIMIT", "3"))


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def run(cmd, cwd):
    try:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        class Result:
            returncode = 127
            stdout = ""
            stderr = str(exc)

        return Result()


def todo_candidates(repo):
    proc = run(["rg", "-n", "--glob", "!**/.git/**", "--glob", "!**/.claude/claudeos/**", "TODO|FIXME"], repo)
    candidates = []
    if proc.returncode not in (0, 1):
        return candidates
    for line in proc.stdout.splitlines()[:50]:
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, lineno, text = parts
        title = f"TODO/FIXME対応: {Path(path).name}:{lineno}"
        candidates.append({
            "title": title,
            "body": f"自動Issue候補です。\n\n- ファイル: `{path}`\n- 行: {lineno}\n- 内容: `{text.strip()}`\n",
            "labels": ["automation", "P3"],
            "source": "todo-fixme",
        })
    return candidates


def state_candidates(state):
    candidates = []
    ci = state.get("ci", {})
    kpi = state.get("kpi", {})
    goal = state.get("goal", {})
    if not goal.get("defined"):
        candidates.append({
            "title": "Goal未定義の解消",
            "body": "Goal Driven Systemの目的が未定義です。大型変更を開始する前に `state.json.goal` を定義してください。",
            "labels": ["automation", "P1"],
            "source": "goal-missing",
        })
    if kpi.get("status") == "unmet":
        candidates.append({
            "title": "KPI未達の改善アクション作成",
            "body": f"KPI未達を検知しました。\n\n- current: `{kpi.get('current_success_rate')}`\n- target: `{kpi.get('success_rate_target')}`\n",
            "labels": ["automation", "kpi", "P2"],
            "source": "kpi-unmet",
        })
    if ci.get("last_run_status") in {"failure", "timed_out", "startup_failure", "action_required"}:
        candidates.append({
            "title": "CI失敗の自動修復",
            "body": f"CI失敗を検知しました。\n\n- status: `{ci.get('last_run_status')}`\n- summary: `{ci.get('last_failure_summary')}`\n",
            "labels": ["automation", "ci", "P1"],
            "source": "ci-failure",
        })
    if ci.get("stable") is False and ci.get("stable_blockers"):
        candidates.append({
            "title": "STABLE未達ブロッカーの解消",
            "body": "STABLE判定の未達項目です。\n\n" + "\n".join(f"- {item}" for item in ci.get("stable_blockers", [])),
            "labels": ["automation", "quality", "P2"],
            "source": "stable-blockers",
        })
    return candidates


def existing_titles(repo):
    proc = run(["gh", "issue", "list", "--state", "open", "--limit", "100", "--json", "title"], repo)
    if proc.returncode != 0:
        return set()
    try:
        return {item.get("title") for item in json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return set()


def create_issues(repo, candidates):
    titles = existing_titles(repo)
    created = []
    for candidate in candidates:
        if len(created) >= CREATE_LIMIT:
            break
        if candidate["title"] in titles:
            continue
        cmd = ["gh", "issue", "create", "--title", candidate["title"], "--body", candidate["body"]]
        for label in candidate.get("labels", []):
            cmd += ["--label", label]
        proc = run(cmd, repo)
        if proc.returncode == 0:
            created.append(proc.stdout.strip())
    return created


def suppress_low_priority(candidates):
    has_p1 = any("P1" in candidate.get("labels", []) for candidate in candidates)
    if not has_p1:
        return candidates
    return [candidate for candidate in candidates if "P3" not in candidate.get("labels", [])]


def main():
    state = load_state()
    repo = state.get("ci", {}).get("repo_path") or state.get("github", {}).get("repo")
    candidates = state_candidates(state)
    if repo and Path(repo).is_dir():
        candidates.extend(todo_candidates(repo))
    candidates = suppress_low_priority(candidates)
    auto_create = AUTO_CREATE_ENV or bool(state.get("automation", {}).get("auto_issue_generation"))

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "auto_create": auto_create,
        "candidates": candidates,
        "created": create_issues(repo, candidates) if auto_create and repo else [],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state.setdefault("automation", {})["issue_factory_last_run_at"] = payload["generated_at"]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
