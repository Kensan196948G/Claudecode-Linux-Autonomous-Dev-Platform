#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from dashboard_actions import discover_project_repositories, run_develop, run_repair_ci, running_action, stop_claude
from manual_control import clear_manual_action, select_project, select_project_path, set_manual_action, update_project

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = DEVOS_HOME / "config/state.json"
PROJECTS = DEVOS_HOME / "config/projects.json"
SELECTED = DEVOS_HOME / "runtime/projects/selected_project.json"
DECISION_LOG = DEVOS_HOME / "runtime/decisions/decision.log"
ORCH_LOG = DEVOS_HOME / "runtime/logs/orchestrator.log"
RECOVERY_LOG = DEVOS_HOME / "runtime/logs/recovery.log"
AGENT_EVENTS = DEVOS_HOME / "runtime/agent_logs/agent_events.log"
CLAUDE_SAFE_LOG = DEVOS_HOME / "runtime/logs/claude-safe.log"
PROJECT_RUNNER_LOG = DEVOS_HOME / "runtime/logs/project-runner.log"
DEVELOPMENT_LOG = DEVOS_HOME / "runtime/agent_logs/development.log"
DASHBOARD_ACTION_LOG = DEVOS_HOME / "runtime/logs/dashboard-actions.log"
CLUSTER_STATE = DEVOS_HOME / "cluster/controller/cluster_state.json"
STRATEGY_SCORES = DEVOS_HOME / "strategy/scores/latest_scores.json"

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>ClaudeCode DevOS ダッシュボード</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="20">
  <script>
    async function refreshCliLogs() {
      try {
        const res = await fetch('/api/logs', {cache: 'no-store'});
        const data = await res.json();
        const updates = {
          'process-snapshot': data.process_snapshot,
          'claude-safe-log': data.claude_safe,
          'development-log': data.development,
          'project-runner-log': data.project_runner,
          'dashboard-action-log': data.dashboard_actions
        };
        for (const [id, value] of Object.entries(updates)) {
          const el = document.getElementById(id);
          if (el) {
            el.textContent = value || '';
          }
        }
        const pidEl = document.getElementById('live-pids');
        if (pidEl) {
          pidEl.textContent = `DashboardジョブPID=${data.running_pid || 'なし'} / Claude PID=${data.claude_pid || 'なし'}`;
        }
      } catch (err) {
        const el = document.getElementById('process-snapshot');
        if (el) {
          el.textContent = `ログ更新に失敗しました: ${err}`;
        }
      }
    }
    window.addEventListener('load', () => {
      refreshCliLogs();
      setInterval(refreshCliLogs, 2000);
    });
  </script>
  <style>
    body { font-family: Arial, sans-serif; margin:20px; background:#f6f8fb; color:#1d2433; }
    h1 { margin-bottom: 6px; }
    .small { color:#666; font-size:13px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; margin-top:16px; }
    .card { background:#fff; border-radius:8px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.08); }
    .kpi { font-size:28px; font-weight:bold; margin-top:8px; }
    .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
    .btn { padding:10px 14px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
    .btn-dev { background:#d9f7e8; }
    .btn-repair { background:#fff1cc; }
    .btn-cool { background:#dfeaff; }
    .btn-stop { background:#ffd6d6; }
    .btn-resume { background:#ececec; }
    select { padding:9px 12px; border:1px solid #bbb; border-radius:8px; }
    input { padding:8px 10px; border:1px solid #bbb; border-radius:8px; max-width:80px; }
    pre { white-space:pre-wrap; word-break:break-word; background:#111; color:#eee; padding:12px; border-radius:8px; font-size:12px; }
    table { width:100%; border-collapse:collapse; font-size:14px; }
    th, td { border-bottom:1px solid #ddd; text-align:left; padding:8px; vertical-align:top; }
    .mono { font-family: Consolas, monospace; }
  </style>
</head>
<body>
  <h1>ClaudeCode DevOS ダッシュボード</h1>
  <div class="small">最終更新: {{ now }}</div>
  {% if notice %}
  <div class="card" style="margin-top:16px; border-left:4px solid #0f766e;">
    <strong>操作結果</strong>
    <div class="small">{{ notice }}</div>
  </div>
  {% endif %}

  <div class="card" style="margin-top:16px;">
    <h3>手動制御</h3>
    <div class="small">手動優先={{ control.manual_override }} / 操作={{ action_labels.get(control.manual_action, control.manual_action) }} / プロジェクト={{ control.manual_project_id }} / 実行中PID={{ running_pid or "なし" }}</div>
    <form method="post" action="/control" class="actions">
      <button class="btn btn-dev" name="action" value="develop">開発を実行</button>
      <button class="btn btn-repair" name="action" value="repair_ci">CI修復を実行</button>
      <button class="btn btn-cool" name="action" value="cooldown">クールダウン</button>
      <button class="btn btn-stop" name="action" value="suspend">停止</button>
      <button class="btn btn-resume" name="action" value="resume">自動判断へ戻す</button>
    </form>
    <form method="post" action="/select-project" class="actions">
      <select name="repo_path">
        {% for project in project_repositories %}
        <option value="{{ project.repository }}" {% if project.repository == selected.repository %}selected{% endif %}>{{ project.name }}</option>
        {% endfor %}
      </select>
      <button class="btn btn-dev" type="submit">プロジェクトを選択</button>
    </form>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>CLI実行状況</h3>
    <div id="live-pids" class="small">DashboardジョブPID={{ running_pid or "なし" }} / Claude PID={{ claude_pid or "なし" }}</div>
    <pre id="process-snapshot">{{ process_snapshot }}</pre>
  </div>

  <div class="grid">
    <div class="card">
      <div>システム状態</div>
      <div class="kpi">{{ system.status }}</div>
      <div class="small">健全性={{ system.health }} / モード={{ decision.current_mode }}</div>
    </div>
    <div class="card">
      <div>次の動作</div>
      <div class="kpi">{{ action_labels.get(decision.next_action, decision.next_action) }}</div>
      <div class="small">{{ decision.reason }}</div>
    </div>
    <div class="card">
      <div>メモリ / Swap</div>
      <div class="kpi">{{ resources.memory_free_mb }} MB</div>
      <div class="small">Swap使用量={{ resources.swap_used_mb }} MB</div>
    </div>
    <div class="card">
      <div>CPU / ディスク</div>
      <div class="kpi">{{ resources.cpu_percent }} %</div>
      <div class="small">ディスク使用率={{ resources.disk_used_percent }} % / 負荷={{ resources.loadavg_1m }}</div>
    </div>
    <div class="card">
      <div>CI状態</div>
      <div class="kpi">{{ ci.last_run_status }}</div>
      <div class="small">修復回数={{ ci.repair_attempt_count }}/{{ ci.repair_attempt_limit }}</div>
    </div>
    <div class="card">
      <div>WorkTree</div>
      <div class="kpi mono">{{ worktree.current_type }}</div>
      <div class="small mono">{{ worktree.current_branch }}</div>
      <div class="small mono">{{ worktree.current_path }}</div>
    </div>
    <div class="card">
      <div>自己進化</div>
      <div class="kpi">{{ evolution.mode }}</div>
      <div class="small">戦略={{ evolution.task_strategy }} / 成功率={{ evolution_success_rate }}</div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>クラスタ</h3>
    <div class="small">モード={{ cluster.cluster.mode }} / 方針={{ cluster.cluster.scheduler_policy }} / リーダー={{ cluster_leader.leader }} / 最終配布={{ cluster.cluster.last_dispatch_at }}</div>
    <table>
      <thead>
        <tr><th>ID</th><th>状態</th><th>退避</th><th>空きメモリ MB</th><th>CPU %</th><th>ジョブ</th><th>ハートビート</th></tr>
      </thead>
      <tbody>
        {% for worker in cluster.workers %}
        <tr>
          <td>{{ worker.id }}</td>
          <td>{{ worker.status }}</td>
          <td>{{ worker.drain }}</td>
          <td>{{ worker.memory_free_mb }}</td>
          <td>{{ worker.cpu_percent }}</td>
          <td>{{ worker.current_jobs }}/{{ worker.max_jobs }}</td>
          <td>{{ worker.last_heartbeat }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <pre>{{ cluster_jobs_json }}</pre>
  </div>

  <div class="grid">
    <div class="card">
      <h3>選択中プロジェクト</h3>
      <pre>{{ selected_json }}</pre>
    </div>
    <div class="card">
      <h3>待機中プロジェクト</h3>
      <pre>{{ queued_json }}</pre>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>戦略スコア</h3>
    <div class="small">モード={{ strategy.mode }} / 最優先={{ strategy.current_top_project }} / 理由={{ strategy.selection_reason }}</div>
    <table>
      <thead>
        <tr><th>プロジェクト</th><th>総合</th><th>ROI</th><th>緊急度</th><th>安定性</th><th>価値</th></tr>
      </thead>
      <tbody>
        {% for score in strategy_scores %}
        <tr>
          <td>{{ score.project_id }} - {{ score.name_ja }}</td>
          <td>{{ score.total_score }}</td>
          <td>{{ score.roi_score }}</td>
          <td>{{ score.urgency_score }}</td>
          <td>{{ score.stability_score }}</td>
          <td>{{ score.value_score }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <div class="small">除外候補={{ strategy.last_dropped_projects }}</div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>プロジェクト編集</h3>
    <table>
      <thead>
        <tr><th>ID</th><th>名前</th><th>優先度</th><th>状態</th><th>期限</th><th>最終実行</th><th>重み</th></tr>
      </thead>
      <tbody>
        {% for project in projects.projects %}
        <tr>
          <td>{{ project.id }}</td>
          <td>{{ project.name_ja }}</td>
          <td>
            <form method="post" action="/projects/update" class="actions">
              <input type="hidden" name="project_id" value="{{ project.id }}">
              <select name="priority">
                {% for value in ["high", "medium", "low"] %}
                <option value="{{ value }}" {% if project.priority == value %}selected{% endif %}>{{ priority_labels.get(value, value) }}</option>
                {% endfor %}
              </select>
          </td>
          <td>
              <select name="status">
                {% for value in ["active", "paused", "blocked", "done", "archived"] %}
                <option value="{{ value }}" {% if project.status == value %}selected{% endif %}>{{ status_labels.get(value, value) }}</option>
                {% endfor %}
              </select>
          </td>
          <td>{{ project.release_due }}</td>
          <td>{{ project.last_run_at }}</td>
          <td>
              <input name="weight" value="{{ project.weight }}">
              <button class="btn btn-resume" type="submit">更新</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="grid">
    <div class="card">
      <h3>プロジェクト実行履歴</h3>
      <pre>{{ project_history_json }}</pre>
    </div>
    <div class="card">
      <h3>CI修復履歴</h3>
      <pre>{{ repair_history_json }}</pre>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>手動操作履歴</h3>
      <pre>{{ manual_history_json }}</pre>
    </div>
    <div class="card">
      <h3>エージェントイベント</h3>
      <pre>{{ agent_events }}</pre>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>意思決定ログ</h3>
      <pre>{{ decision_log }}</pre>
    </div>
    <div class="card">
      <h3>オーケストレータログ</h3>
      <pre>{{ orchestrator_log }}</pre>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>復旧ログ</h3>
    <pre>{{ recovery_log }}</pre>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Claude実行ログ</h3>
      <pre id="claude-safe-log">{{ claude_safe_log }}</pre>
    </div>
    <div class="card">
      <h3>開発実行ログ</h3>
      <pre id="development-log">{{ development_log }}</pre>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>プロジェクトランナーログ</h3>
      <pre id="project-runner-log">{{ project_runner_log }}</pre>
    </div>
    <div class="card">
      <h3>Dashboard操作ログ</h3>
      <pre id="dashboard-action-log">{{ dashboard_action_log }}</pre>
    </div>
  </div>
</body>
</html>
"""


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def tail(path, count=60):
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-count:])


def pretty(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def touch_dashboard():
    updater = DEVOS_HOME / "web/update_dashboard_state.py"
    subprocess.run([str(updater)], check=False)


def pid_from_file(path):
    if not path.exists():
        return None
    pid = path.read_text(encoding="utf-8").strip()
    return pid or None


def process_snapshot():
    keywords = (
        "/opt/claudecode-devos",
        "/home/kensan/.local/bin/claude",
        "/home/kensan/.local/share/claude/versions",
        "claude --dangerously",
        "claude-safe",
        "run-scheduled",
        "run-auto",
        "dashboard-action",
    )
    excludes = ("claude-mem", ".claude/plugins", ".claude-mem", "chroma-mcp")
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,ppid,stat,etime,cmd"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"プロセス取得に失敗しました: {exc}"
    lines = proc.stdout.splitlines()
    if not lines:
        return "関連プロセスはありません。"
    header, body = lines[0], lines[1:]
    picked = [
        line for line in body
        if any(keyword in line for keyword in keywords)
        and not any(exclude in line for exclude in excludes)
        and "gunicorn" not in line
    ]
    if not picked:
        return "関連プロセスはありません。"
    return "\n".join([header, *picked[-40:]])


ACTION_LABELS = {
    None: "なし",
    "": "なし",
    "idle": "待機",
    "develop": "開発",
    "repair_ci": "CI修復",
    "cooldown": "クールダウン",
    "suspend": "停止",
    "resume": "自動判断へ復帰",
}

PRIORITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

STATUS_LABELS = {
    "active": "実行対象",
    "paused": "一時停止",
    "blocked": "ブロック中",
    "done": "完了",
    "archived": "アーカイブ済み",
}


@app.route("/")
def index():
    touch_dashboard()
    state = load_json(STATE, {})
    projects = load_json(PROJECTS, {"projects": []})
    selected = load_json(SELECTED, {})
    cluster = load_json(CLUSTER_STATE, {"cluster": {}, "workers": [], "jobs": {}})
    cluster_leader = load_json(DEVOS_HOME / "cluster/leader/leader.json", {})
    strategy_scores = load_json(STRATEGY_SCORES, {"scores": []})
    runtime = state.get("projects_runtime", {})
    history = state.get("history", {})
    evolution = state.get("evolution", {})
    evolution_metrics = evolution.get("last_metrics") or {}
    return render_template_string(
        HTML,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        projects=projects,
        project_repositories=discover_project_repositories(),
        selected_json=pretty(selected),
        selected=selected,
        cluster=cluster,
        cluster_leader=cluster_leader,
        cluster_jobs_json=pretty(cluster.get("jobs", {})),
        strategy=state.get("strategy", {}),
        strategy_scores=strategy_scores.get("scores", [])[:5],
        queued_json=pretty(runtime.get("queued_projects", [])),
        project_history_json=pretty(history.get("last_project_runs", [])),
        repair_history_json=pretty(history.get("last_ci_repairs", [])),
        manual_history_json=pretty(history.get("last_manual_actions", [])),
        system=state.get("system", {}),
        decision=state.get("decision", {}),
        resources=state.get("resources", {}),
        ci=state.get("ci", {}),
        control=state.get("control", {}),
        scheduler=state.get("scheduler", {}),
        worktree=state.get("worktree", {}),
        evolution=evolution,
        evolution_success_rate=evolution_metrics.get("success_rate"),
        action_labels=ACTION_LABELS,
        priority_labels=PRIORITY_LABELS,
        status_labels=STATUS_LABELS,
        running_pid=running_action(),
        claude_pid=pid_from_file(DEVOS_HOME / "runtime/pids/claude.pid"),
        process_snapshot=process_snapshot(),
        notice=request.args.get("notice", ""),
        decision_log=tail(DECISION_LOG),
        orchestrator_log=tail(ORCH_LOG),
        recovery_log=tail(RECOVERY_LOG),
        agent_events=tail(AGENT_EVENTS),
        claude_safe_log=tail(CLAUDE_SAFE_LOG, 100),
        project_runner_log=tail(PROJECT_RUNNER_LOG, 100),
        development_log=tail(DEVELOPMENT_LOG, 100),
        dashboard_action_log=tail(DASHBOARD_ACTION_LOG, 100),
    )


@app.route("/control", methods=["POST"])
def control():
    action = request.form.get("action", "")
    notice = ""
    if action == "resume":
        clear_manual_action()
        notice = "自動判断へ戻しました。"
    elif action in {"develop", "repair_ci", "cooldown", "suspend"}:
        set_manual_action(action, "requested from dashboard")
        if action == "develop":
            _, notice = run_develop()
        elif action == "repair_ci":
            _, notice = run_repair_ci()
        elif action == "suspend":
            _, notice = stop_claude()
        else:
            notice = "クールダウンを設定しました。"
    return redirect(url_for("index", notice=notice))


@app.route("/select-project", methods=["POST"])
def select_project_route():
    repo_path = request.form.get("repo_path", "")
    project_id = request.form.get("project_id", "")
    notice = ""
    if repo_path:
        project = select_project_path(repo_path)
        notice = f"プロジェクトを選択しました: {project['id']}"
    elif project_id:
        select_project(project_id)
        notice = f"プロジェクトを選択しました: {project_id}"
    return redirect(url_for("index", notice=notice))


@app.route("/projects/update", methods=["POST"])
def update_project_route():
    project_id = request.form.get("project_id", "")
    priority = request.form.get("priority", "")
    status = request.form.get("status", "")
    weight = request.form.get("weight", "0")
    if project_id:
        update_project(project_id, priority, status, weight)
    return redirect(url_for("index"))


@app.route("/api/state")
def api_state():
    return jsonify(load_json(STATE, {}))


@app.route("/api/projects")
def api_projects():
    return jsonify(load_json(PROJECTS, {"projects": []}))


@app.route("/api/cluster")
def api_cluster():
    return jsonify(load_json(CLUSTER_STATE, {}))


@app.route("/api/strategy")
def api_strategy():
    return jsonify(load_json(STRATEGY_SCORES, {"scores": []}))


@app.route("/api/logs")
def api_logs():
    return jsonify({
        "claude_safe": tail(CLAUDE_SAFE_LOG, 100),
        "project_runner": tail(PROJECT_RUNNER_LOG, 100),
        "development": tail(DEVELOPMENT_LOG, 100),
        "dashboard_actions": tail(DASHBOARD_ACTION_LOG, 100),
        "process_snapshot": process_snapshot(),
        "running_pid": running_action(),
        "claude_pid": pid_from_file(DEVOS_HOME / "runtime/pids/claude.pid"),
    })


if __name__ == "__main__":
    state = load_json(STATE, {})
    dashboard = state.get("dashboard", {})
    app.run(
        host=os.environ.get("DEVOS_DASHBOARD_HOST", dashboard.get("host", "0.0.0.0")),
        port=int(os.environ.get("DEVOS_DASHBOARD_PORT", dashboard.get("port", 5050))),
    )
