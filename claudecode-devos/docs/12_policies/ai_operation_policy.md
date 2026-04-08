# ClaudeOS AI Operation Policy

## Purpose
本システムは自律開発を行うが、安全性と品質を最優先とする。

## Principles
- 無限ループは禁止する。
- CI修復は `ci.repair_attempt_limit` 以下に制限する。上限は10回まで。
- 本番ブランチ、base branch、main への直接 push を禁止する。
- 重大変更はPRレビューを通す。
- `state.json` はロック付き更新とatomic writeを使う。

## Priority
1. Stability
2. Quality
3. Speed

## Prohibited
- 強制実行
- 無限リトライ
- `state.json` の手動破壊
- Secrets のGit管理
- WorkTreeなしの自律コード変更
