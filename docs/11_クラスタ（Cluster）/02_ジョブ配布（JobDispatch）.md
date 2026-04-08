# 02_ジョブ配布（JobDispatch）

## 位置づけ
この文書は `11_クラスタ（Cluster）` に属する運用ドキュメントです。

## 目的
least-loaded方針、tags、drain判定を説明する。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- required_tags
- current_jobs
- max_jobs
- priority

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] required_tags の設定または運用状態を確認する
- [ ] current_jobs の設定または運用状態を確認する
- [ ] max_jobs の設定または運用状態を確認する
- [ ] priority の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
