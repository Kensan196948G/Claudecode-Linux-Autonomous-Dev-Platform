# 01_進化ループ（EvolutionLoop）

## 位置づけ
この文書は `17_自己進化（Evolution）` に属する運用ドキュメントです。

## 目的
実行ログ、分析、最適化、プロンプト反映の流れを説明する。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- log_collector
- analyzer
- optimizer
- prompt_optimizer

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] log_collector の設定または運用状態を確認する
- [ ] analyzer の設定または運用状態を確認する
- [ ] optimizer の設定または運用状態を確認する
- [ ] prompt_optimizer の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
