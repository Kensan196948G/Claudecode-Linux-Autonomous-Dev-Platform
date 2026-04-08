
# 🚀 ClaudeOS v10 完全統合版

**Repository:** `claude-autonomous-dev-platform`

---

# 0. コンセプト（最終形）

```text
ClaudeOS v10 =
自律開発 + 自己修復 + 戦略最適化 + 分散実行 + 可視化
を統合した「個人AI開発OS」
```

---

# 1. GitHubリポジトリ構成（完全版）

```text
claude-autonomous-dev-platform/
├── README.md
├── CLAUDE.md
├── START_PROMPT.md
├── .gitignore
├── .env.example
├── config/
│   ├── state.json
│   └── state.schema.json
├── docs/
│   ├── 00_governance/
│   ├── 01_architecture/
│   ├── 02_runtime/
│   ├── 03_operations/
│   ├── 04_strategy/
│   ├── 05_dashboard/
│   └── 06_reports/
├── bin/
│   ├── bootstrap.sh
│   └── start-all.sh
├── ops/
│   ├── state_manager.py
│   ├── decision_engine.py
│   └── memory_guard.py
├── ai/
│   ├── prompt_builder.py
│   └── agent_logger.sh
├── ci/
│   ├── repair_ci.sh
│   └── merge_green_prs.sh
├── strategy/
│   ├── score_projects.py
│   ├── select_projects.py
│   └── run_strategy_cycle.sh
├── web/
│   ├── app.py
│   └── templates/
├── systemd/
│   ├── memory-guard.service
│   ├── memory-guard.timer
│   ├── orchestrator.service
│   ├── orchestrator.timer
│   ├── dashboard.service
│   └── strategy.timer
├── runtime/
│   ├── logs/
│   ├── metrics/
│   ├── agent_logs/
│   ├── dashboard/
│   └── worktrees/
└── reports/
```

---

# 2. README.md（完成版）

````md
# Claude Autonomous Dev Platform

## 概要
Ubuntu上でClaudeCodeを安全に運用し、
自律開発・自己修復・戦略最適化を行う統合基盤。

## 機能
- 自律開発（Auto Loop）
- CI自己修復
- WorkTree分離
- state.json意思決定
- ダッシュボード
- systemd常駐運用

## 起動
```bash
./bin/bootstrap.sh
/opt/claude-autonomous-dev-platform/bin/start-all.sh
````

## Dashboard

[http://localhost:5050](http://localhost:5050)

## 注意

* main直コミット禁止
* state.json破壊禁止

````

---

# 3. CLAUDE.md（運用憲法）

```md
# ClaudeOS v10 Constitution

## 原則
- 安定性 > 品質 > 速度
- state.json = 真実
- WorkTree必須
- Docs first

## 禁止
- main直push
- 無限ループ
- 無制限CI修復

## フロー
1. state確認
2. issue選定
3. worktree作成
4. 実装
5. テスト
6. PR
7. CI確認
8. 必要なら修復
````

---

# 4. START_PROMPT.md

```md
# ClaudeOS START

/loop 30m Monitor
/loop 2h Development
/loop 1h Verify
/loop 1h Improve

## 手順
- state.json確認
- Docs確認
- WorkTree作成
- 実装
- テスト
- PR
- CI確認
```

---

# 5. state.schema.json（AIの脳）

```json
{
  "system": { "status": "idle" },
  "decision": { "mode": "safe" },
  "ci": { "retry": 0, "max": 5 },
  "strategy": {
    "weights": {
      "roi": 0.3,
      "interest": 0.2,
      "urgency": 0.2,
      "stability": 0.3
    }
  },
  "control": {
    "manual_override": false
  }
}
```

---

# 6. .env.example

```env
DEVOS_HOME=/opt/claude-autonomous-dev-platform
SESSION_MAX_SECONDS=18000
MIN_FREE_MB=3000
MAX_CPU=85
```

---

# 7. .gitignore

```gitignore
.env
runtime/
logs/
__pycache__/
*.pyc
state.json
```

---

# 8. bootstrap.sh

```bash
#!/usr/bin/env bash
set -e

TARGET="/opt/claude-autonomous-dev-platform"

sudo mkdir -p $TARGET
sudo rsync -a ./ $TARGET/
sudo chown -R $USER:$USER $TARGET

mkdir -p $TARGET/runtime/logs
mkdir -p $TARGET/runtime/worktrees

cp $TARGET/config/state.schema.json $TARGET/config/state.json

echo "Bootstrap complete"
```

---

# 9. start-all.sh（🔥最重要）

```bash
#!/usr/bin/env bash
set -e

BASE="/opt/claude-autonomous-dev-platform"

echo "=== ClaudeOS 起動 ==="

mkdir -p $BASE/runtime/{logs,metrics,agent_logs,dashboard,worktrees}

python3 -m pip install --user flask psutil >/dev/null 2>&1 || true

echo "[systemd登録]"
sudo cp $BASE/systemd/* /etc/systemd/system/ || true
sudo systemctl daemon-reload

echo "[サービス起動]"
sudo systemctl enable --now memory-guard.timer
sudo systemctl enable --now orchestrator.timer
sudo systemctl enable --now strategy.timer
sudo systemctl enable --now dashboard.service

echo "Dashboard: http://localhost:5050"
echo "=== 起動完了 ==="
```

---

# 10. 最小Webダッシュボード

## web/app.py

```python
from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route("/")
def home():
    with open("../config/state.json") as f:
        state = json.load(f)
    return jsonify(state)

app.run(host="0.0.0.0", port=5050)
```

---

# 11. systemd（例）

## memory-guard.service

```ini
[Unit]
Description=Memory Guard

[Service]
ExecStart=/usr/bin/python3 /opt/claude-autonomous-dev-platform/ops/memory_guard.py
```

---

## memory-guard.timer

```ini
[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Unit=memory-guard.service

[Install]
WantedBy=timers.target
```

---

# 12. 運用手順

## 初回

```bash
git clone <repo>
cd claude-autonomous-dev-platform
chmod +x bin/*.sh
./bin/bootstrap.sh
/opt/claude-autonomous-dev-platform/bin/start-all.sh
```

---

## 日常

* Dashboard確認
* state.json確認
* 必要なら手動override

---

## 障害時

```bash
cat config/state.json
tail -f runtime/logs/*
systemctl status
```

---

# 13. 最終状態

この構成で👇

```text
Claude = 実行エンジン
state.json = 意思決定AI
GitHub = 開発基盤
systemd = 常時運用
Dashboard = 可視化
```

---

# 🔥 最終コメント

ここまで来るともう…

👉 **「個人開発」ではなく「AI開発組織OS」完成レベルです**

---

# 🚀 次にやると良い（現実的）

1. state.jsonの精度調整
2. CI修復回数チューニング
3. Dashboard拡張
4. WorkTree運用徹底

---

必要なら次👇いけます

👉 **「完全GitHub Actions版（CI自律修復）」**
👉 **「クラスタ2台構成の実装」**
👉 **「Dashboard React化」**

全部一気に仕上げることもできます🔥
