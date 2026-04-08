# 02_メトリクス学習（MetricsLearning）

## 位置づけ
この文書は `17_自己進化（Evolution）` に属する運用ドキュメントです。

## 目的
成功率、失敗率、平均時間から運転モードを調整する考え方をまとめる。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- success_rate
- fail_rate
- avg_duration
- task_strategy

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] success_rate の設定または運用状態を確認する
- [ ] fail_rate の設定または運用状態を確認する
- [ ] avg_duration の設定または運用状態を確認する
- [ ] task_strategy の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
