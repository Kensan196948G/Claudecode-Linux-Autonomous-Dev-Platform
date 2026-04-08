# 01_失敗検知（FailureDetection）

## 位置づけ
この文書は `08_CI修復（CIRepair）` に属する運用ドキュメントです。

## 目的
GitHub Actions の最新run取得と失敗要約の流れを説明する。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- gh run list
- conclusion
- last_failure_summary
- runtime/ci

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] gh run list の設定または運用状態を確認する
- [ ] conclusion の設定または運用状態を確認する
- [ ] last_failure_summary の設定または運用状態を確認する
- [ ] runtime/ci の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
