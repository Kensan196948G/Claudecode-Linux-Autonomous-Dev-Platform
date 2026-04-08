# 🐧 ClaudeCode Linux Autonomous Dev Platform

![Platform](https://img.shields.io/badge/platform-Ubuntu%20Linux-E95420?logo=ubuntu&logoColor=white)
![Runtime](https://img.shields.io/badge/runtime-Bash%20%2B%20Python-3776AB?logo=python&logoColor=white)
![Systemd](https://img.shields.io/badge/orchestration-systemd-2A6DB0?logo=linux&logoColor=white)
![ClaudeCode](https://img.shields.io/badge/ClaudeCode-safe%20runner-111827)
![Docs First](https://img.shields.io/badge/docs-first-0F766E)
![Auto Healing](https://img.shields.io/badge/auto--healing-enabled-16A34A)

## 🌟 目的

**ClaudeCode Linux Autonomous Dev Platform** は、Ubuntuネイティブ環境でClaudeCodeを長時間運用するための自律開発基盤です。

🧠 `state.json` を中枢に、🛡️ `claude-safe`、📊 `memory_guard`、♻️ Auto Healing、🗂️ Docs First、⏱️ systemd timerを組み合わせ、**落ちないことより、落ちても自動復帰すること**を優先します。

---

## 🧭 コンセプトマップ

```mermaid
mindmap
  root((🐧 ClaudeCode DevOS))
    🧠 State
      state.json
      recovery_count
      active_project
      resource metrics
    🛡️ Safe Runner
      ulimit
      nice
      ionice
      oom_score_adj
    📊 Observability
      memory
      swap
      cpu
      load average
      disk
    ♻️ Auto Healing
      stop pytest
      stop Claude PID
      refresh swap
      restart safe runner
    🗂️ Docs First
      governance
      operations
      reports
      decisions
    🚀 GitHub
      Actions
      Issues
      Projects
      Roadmap
```

---

## 🏗️ 全体アーキテクチャ

```mermaid
flowchart TD
  A["⏱️ systemd timer<br/>claudecode-session.timer"] --> B["🚀 run-session.sh"]
  B --> C["📌 project-dispatcher.sh"]
  C --> D["🗂️ Project Repository + Docs"]
  D --> E["🧩 Prompt Composer<br/>session_context + state.json + START_PROMPT"]
  E --> F["🛡️ claude-safe.sh"]
  F --> G["🤖 ClaudeCode<br/>--dangerously-skip-permissions"]

  H["⏱️ systemd timer<br/>memory-guard.timer"] --> I["📊 memory_guard.py"]
  I --> J["🧠 state_manager.py"]
  I --> K{"🚨 Memory / Swap<br/>threshold breached?"}
  K -- "No" --> L["✅ health=healthy / warning"]
  K -- "Yes" --> M["♻️ recovery.sh"]
  M --> N["🧪 stop pytest"]
  M --> O["🤖 stop Claude PID"]
  M --> P["💽 refresh swap if sudo allows"]
  M --> Q["🔁 restart claude-safe"]
  M --> J
```

---

## 🔁 ClaudeOS 5時間ループ

```mermaid
sequenceDiagram
  autonumber
  participant Timer as ⏱️ systemd
  participant Session as 🚀 run-session.sh
  participant State as 🧠 state.json
  participant Docs as 🗂️ Docs
  participant Safe as 🛡️ claude-safe
  participant Claude as 🤖 ClaudeCode

  Timer->>Session: Start daily session
  Session->>State: status=running / last_session_start
  Session->>Docs: Write session_context.md
  Session->>State: Read latest runtime state
  Session->>Safe: Launch with composed prompt
  Safe->>Claude: ulimit + nice + ionice + OOM score
  Claude->>Docs: Update reports and decisions
  Session->>State: status=idle / last_session_end
```

---

## ♻️ Auto Healing 判定フロー

```mermaid
stateDiagram-v2
  [*] --> Healthy: ✅ normal metrics
  Healthy --> Warning: ⚠️ CPU/load/disk high
  Healthy --> Recovering: 🚨 memory low or swap high
  Warning --> Recovering: 🚨 memory low or swap high
  Recovering --> StopTests: 🧪 pkill pytest
  StopTests --> StopClaude: 🤖 stop recorded Claude PID
  StopClaude --> RefreshSwap: 💽 swapoff/swapon if non-interactive sudo works
  RefreshSwap --> RestartClaude: 🔁 claude-safe restart
  RestartClaude --> Warning: 🧠 recovery_count++
  Warning --> Healthy: ✅ metrics normalized
```

---

## 📦 ディレクトリ構成

```text
claudecode-devos/
├── 🧰 bin/
│   ├── claude-safe.sh
│   ├── run-session.sh
│   ├── project-dispatcher.sh
│   └── backup-docs.sh
├── ⚙️ config/
│   ├── devos.env
│   ├── projects.json
│   └── state.json
├── 🗂️ docs/
│   ├── 00_governance/
│   ├── 01_projects/
│   ├── 02_architecture/
│   ├── 03_operations/
│   ├── 04_logs/
│   ├── 05_reports/
│   └── 06_decisions/
├── 🧠 ops/
│   ├── memory_guard.py
│   ├── recovery.sh
│   ├── state_manager.py
│   └── metrics_snapshot.py
├── 🏃 runtime/
│   ├── logs/
│   ├── pids/
│   ├── tmp/
│   └── metrics/
└── ⏱️ systemd/
    ├── claudecode-session.service
    ├── claudecode-session.timer
    ├── memory-guard.service
    └── memory-guard.timer
```

---

## 🚀 クイックスタート

```bash
sudo SERVICE_USER=kensan ./claudecode-devos/install.sh
python3 -m pip install --user -r /opt/claudecode-devos/requirements.txt
sudo systemctl enable --now memory-guard.timer
sudo systemctl enable --now claudecode-session.timer
```

### ✅ ローカル検証

```bash
DEVOS_HOME="$PWD/claudecode-devos" python3 claudecode-devos/ops/state_manager.py get system.status
DEVOS_HOME="$PWD/claudecode-devos" python3 claudecode-devos/ops/metrics_snapshot.py
DEVOS_HOME="$PWD/claudecode-devos" MIN_FREE_MB=0 MAX_SWAP_USED_MB=999999 python3 claudecode-devos/ops/memory_guard.py
```

---

## 🧠 state.json の役割

```mermaid
erDiagram
  STATE_JSON ||--|| SYSTEM : tracks
  STATE_JSON ||--|| RESOURCES : records
  STATE_JSON ||--|| CLAUDE : controls
  STATE_JSON ||--|| PROJECTS : selects

  SYSTEM {
    string status
    string mode
    string health
    string last_error
    int recovery_count
  }
  RESOURCES {
    float memory_free_mb
    float swap_used_mb
    float cpu_percent
    float loadavg_1m
    float disk_used_percent
  }
  CLAUDE {
    string status
    int last_pid
    string last_command
    bool dangerously_skip_permissions
  }
  PROJECTS {
    string active_project
    int registered_count
    string last_project_switch
  }
```

---

## 🛠️ GitHub Actions

このリポジトリでは、GitHub ActionsをCI/運用検証に使います。

| Workflow | 役割 | 主な検証 |
| --- | --- | --- |
| 🧪 `ci.yml` | Bash/Python検証 | `shellcheck`, `py_compile`, JSON validation |
| 📚 `docs-health.yml` | Docs健全性 | README、運用Docs、Mermaidブロックの存在確認 |
| 📌 `project-automation.yml` | GitHub Projects連携 | Issue/PRをProjectへ自動追加 |

```mermaid
flowchart LR
  Push["📤 push / pull_request"] --> CI["🧪 CI"]
  CI --> Bash["🐚 shellcheck"]
  CI --> Python["🐍 py_compile"]
  CI --> JSON["🧾 json.tool"]
  CI --> Docs["📚 docs-health"]
  Issue["📝 issue opened"] --> Project["📌 GitHub Projects"]
  PR["🔀 pull_request opened"] --> Project
```

---

## 📌 GitHub Projects 運用

GitHub Projectsはリポジトリ設定で有効化済みです。推奨ボード:

🎯 **ClaudeCode DevOS Roadmap**

| View | 用途 |
| --- | --- |
| 🧭 Roadmap | 6か月ロードマップ |
| 🧪 CI / Quality | GitHub Actions失敗、テスト、検証 |
| ♻️ Auto Healing | OOM、memory guard、recovery改善 |
| 🗂️ Docs First | Docs、日報、decision log |
| 🚀 Release | 183日リリース目標の管理 |

Project連携ワークフローを動かすには、Repository Secretに `PROJECTS_TOKEN` を設定し、`PROJECT_URL` を対象Project URLに差し替えてください。

---

## 🗺️ 開発ロードマップ

```mermaid
gantt
  title 🗺️ ClaudeCode DevOS 6-Month Roadmap
  dateFormat  YYYY-MM-DD
  section Phase 1
  🛡️ OOM対策・claude-safe・state管理 :done, p1, 2026-04-08, 14d
  section Phase 2
  📩 Gmail通知・daily/weekly usage・金曜13時reset :active, p2, 2026-04-22, 21d
  section Phase 3
  🐙 GitHub Actions / Issues / Projects連動 :p3, 2026-05-13, 28d
  section Phase 4
  🧠 Prompt自動合成・slow/full mode切替 :p4, 2026-06-10, 35d
  section Phase 5
  🚀 6か月運用・安定化・リリース :p5, 2026-07-15, 85d
```

---

## ⚠️ 運用上の注意

- 🧨 `--dangerously-skip-permissions` 前提のため、対象リポジトリと実行ユーザーを限定してください。
- 🛡️ `claude-safe.sh` 経由で起動し、直接 `claude` を常時実行しないでください。
- 💽 swap refreshは `sudo -n` が通る場合のみ実行されます。
- 📊 CPU/load/diskはwarning扱い、memory/swap異常をrecovery発火条件にしています。
- 🗂️ DocsをSingle Source of Truthとして更新してください。

---

## 📚 関連ドキュメント

- 🧰 [DevOS配布ツリー](./claudecode-devos/README.md)
- 📚 [ルートDocs索引](./docs/00_索引（Index）.md)
- 🛡️ [運用ポリシー](./claudecode-devos/docs/00_governance/operations_policy.md)
- 📊 [ランタイムルール](./claudecode-devos/docs/03_operations/runtime_rules.md)
- 🧠 [アーキテクチャ概要](./claudecode-devos/docs/02_architecture/overview.md)
- 📌 [GitHub運用メモ](./docs/07_GitHub連携（GitHubIntegration）/03_ProjectsとActions（ProjectsAndActions）.md)
