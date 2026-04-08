# 02_修復プロンプト（RepairPrompt）

## 位置づけ
この文書は `08_CI修復（CIRepair）` に属する運用ドキュメントです。

## 目的
CI失敗要約からClaude修復プロンプトを合成する方針をまとめる。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- 原因候補
- 最小変更
- 局所テスト
- Docs更新

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] 原因候補 の設定または運用状態を確認する
- [ ] 最小変更 の設定または運用状態を確認する
- [ ] 局所テスト の設定または運用状態を確認する
- [ ] Docs更新 の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
