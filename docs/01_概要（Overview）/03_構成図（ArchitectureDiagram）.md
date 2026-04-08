# 03_構成図（ArchitectureDiagram）

## 位置づけ
この文書は `01_概要（Overview）` に属する運用ドキュメントです。

## 目的
Claude実行、監視、復旧、CI修復、ダッシュボード、クラスタの関係を説明する。

## 対象読者
- DevOS を導入・運用する管理者
- ClaudeCode の自律実行を監視する担当者
- GitHub Actions / Projects / systemd の状態を確認する担当者

## 主要トピック
- 単体構成
- 分散構成
- データフロー
- 責務分離

## 運用メモ
- 変更時は `state.json`、`projects.json`、Dashboard 表示、systemd 状態の整合性を確認する。
- 自律実行に関わる設定は、最初に安全側の値で試験し、ログを確認してから強める。
- GitHub 連携を変更する場合は、PR、CI、Projects への反映を必ず確認する。

## 確認チェックリスト
- [ ] 単体構成 の設定または運用状態を確認する
- [ ] 分散構成 の設定または運用状態を確認する
- [ ] データフロー の設定または運用状態を確認する
- [ ] 責務分離 の設定または運用状態を確認する

## 関連ファイル
- `claudecode-devos/config/state.json`
- `claudecode-devos/config/projects.json`
- `claudecode-devos/config/devos.env`
- `claudecode-devos/docs/`
