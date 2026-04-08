# Memory 使い分けガイド

ClaudeOS では「記憶」に3種類の保存先を使い分ける。

## 保存先の比較

| 項目 | Memory MCP | `~/.claude/projects/*/memory/` | `state.json` |
|------|-----------|-------------------------------|--------------|
| スコープ | グローバル（全プロジェクト共通） | プロジェクト単位 | セッション跨ぎの動的状態 |
| 永続性 | セッション間で引き継がれる | セッション間で引き継がれる | セッション間で引き継がれる |
| 主な用途 | ユーザーの好み・フィードバック・学習済み事実 | プロジェクト固有の知識・設計判断 | システムの現在状態 |
| 検索方法 | MCP の `search` / `get_observations` | `Read` / `Grep` | `state_manager.py get` |
| 書き込みタイミング | セッション終了前 / 重要な判断後 | コードに埋め込めない文脈の保存時 | ツール実行後（hooks 経由） |

## Memory MCP に保存するもの

- ユーザーへのフィードバック（「この方法で進めて」「これはやめて」）
- ユーザーの技術スタック・経験レベル
- プロジェクト横断的な設計判断の理由
- 外部システムのリソース場所（Linear, Grafana, Slack チャンネルなど）

**保存しないもの:**
- コードのパターンや規約（コードから読める）
- git 履歴・誰が何を変えたか（`git log` が正）
- デバッグの解決手順（コミットメッセージに記録済み）
- 一時的なタスク進捗

## `~/.claude/projects/*/memory/` に保存するもの

- `user_*.md` — ユーザープロファイル・役割・好み
- `feedback_*.md` — アプローチへの指示（何をすべき/すべきでないか）
- `project_*.md` — 進行中の取り組み・締め切り・ステークホルダー
- `reference_*.md` — 外部システムへのポインタ

フォーマット:
```markdown
---
name: <記憶の名前>
description: <1行の説明 — 将来の検索用>
type: user|feedback|project|reference
---

<内容>
```

## `state.json` に保存するもの

動的なシステム状態のみ。セッションまたぎで変化する値:

- `system.status` — active / idle / error
- `ci.*` — 最終 CI 結果、修復試行回数
- `kpi.*` — 現在の成功率、最終評価日時
- `execution.remaining_seconds` — 残り作業時間
- `automation.auto_issue_generation` — フラグ（decision_engine が更新）

**保存しないもの:**
- 大容量の API レスポンス（→ `runtime/github/projects_cache.json` のような外部ファイルへ）
- 履歴ログ（→ `runtime/decisions/*.log` へ）

## 書き込みタイミングの原則

```
セッション終了前  → Memory MCP + ~/.claude/projects/*/memory/ に重要事実を保存
ツール実行後     → state.json を hooks 経由で更新（system.status = active）
ループ完了時     → state.json の execution / kpi セクションを更新
```

## 読み込みタイミングの原則

```
セッション開始時  → Memory MCP を確認して前回作業を引き継ぐ
コンテキスト不足時 → memory/*.md を Read で参照
状態確認時       → state_manager.py get <key>
```
