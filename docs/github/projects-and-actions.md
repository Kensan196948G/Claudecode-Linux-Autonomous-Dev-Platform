# 🐙 GitHub Actions / Projects 運用メモ

## ✅ 現在の方針

- 🧪 GitHub ActionsでBash、Python、JSON、Docsの健全性を検証する。
- 📌 GitHub Projectsで6か月ロードマップ、Auto Healing、Docs First、CI品質を管理する。
- 📝 IssuesはProjectへ自動追加し、運用・改善・障害を一箇所に集約する。

## 📌 Project Automation設定

1. GitHub Projectを作成する。
2. Project URLをRepository Variable `PROJECT_URL` に設定する。
3. `project` scopeを持つPATをRepository Secret `PROJECTS_TOKEN` に設定する。
4. `.github/workflows/project-automation.yml` を有効化する。

## 🧭 推奨Project Views

| View | Filter |
| --- | --- |
| 🧭 Roadmap | milestone / iteration |
| 🚨 Incidents | label:`incident` |
| ♻️ Auto Healing | label:`auto-healing` |
| 📚 Docs | label:`docs` |
| 🧪 CI | label:`ci` |

## 🧪 Actions

| Workflow | Trigger |
| --- | --- |
| 🧪 CI | push, pull_request, workflow_dispatch |
| 📚 Docs Health | push, pull_request, workflow_dispatch |
| 📌 Project Automation | issues, pull_request, workflow_dispatch |

