# 03_ProjectsとActions（ProjectsAndActions）

## 位置づけ
この文書は `07_GitHub連携（GitHubIntegration）` に属する運用ドキュメントです。

## 目的
GitHub Projects と Actions の接続条件、必要な変数・secretをまとめる。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- PROJECT_URL
- PROJECTS_TOKEN
- workflow
- permissions

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] PROJECT_URL の設定または運用状態を確認する
- [ ] PROJECTS_TOKEN の設定または運用状態を確認する
- [ ] workflow の設定または運用状態を確認する
- [ ] permissions の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`

## 現在の方針
- GitHub ActionsでBash、Python、JSON、Docsの健全性を検証する。
- GitHub Projectsで6か月ロードマップ、Auto Healing、Docs First、CI品質を管理する。
- IssuesとPull RequestsはProjectへ自動追加し、運用・改善・障害を一箇所に集約する。

## Project Automation設定
1. GitHub Projectを作成または選定する。現在は `ClaudeCode DevOS Roadmap` を利用する。
2. Project URLをRepository Variable `PROJECT_URL` に設定する。現在値は `https://github.com/users/Kensan196948G/projects/18`。
3. `project` scopeを持つPATをRepository Secret `PROJECTS_TOKEN` に設定する。
4. `.github/workflows/project-automation.yml` を有効化する。
5. IssueまたはPull Requestを作成し、Projectへ追加されることを確認する。

## 推奨Project Views
| View | Filter |
| --- | --- |
| Roadmap | milestone / iteration |
| Incidents | label:`incident` |
| Auto Healing | label:`auto-healing` |
| Docs | label:`docs` |
| CI | label:`ci` |

## Actions
| Workflow | Trigger |
| --- | --- |
| CI | push, pull_request, workflow_dispatch |
| Docs Health | push, pull_request, workflow_dispatch |
| Project Automation | issues, pull_request, workflow_dispatch |

## 設定確認コマンド
```bash
gh api repos/Kensan196948G/Claudecode-Linux-Autonomous-Dev-Platform/actions/permissions
gh workflow list --repo Kensan196948G/Claudecode-Linux-Autonomous-Dev-Platform --all
gh variable list --repo Kensan196948G/Claudecode-Linux-Autonomous-Dev-Platform
gh secret list --repo Kensan196948G/Claudecode-Linux-Autonomous-Dev-Platform
```
