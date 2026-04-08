# State Schema Policy

## Purpose
`state.json` は DevOS の判断基盤であり、破損時は自律実行を停止する。

## Schema
- Machine-readable schema: `config/state.schema.json`
- Agent event schema: `config/agent_log.schema.json`
- Runtime validator: `ops/validate_config.py`

## Rules
- 新しいトップレベルキーを追加した場合は schema と docs を更新する。
- 自動更新は `state_manager.py` かロック付き atomic write を使う。
- `ci.repair_attempt_limit` は10以下にする。
- `decision.next_action` は `idle`, `develop`, `verify`, `repair_ci`, `cooldown`, `suspend` の範囲にする。
- `github.auto_merge_enabled` と `ci.auto_merge_enabled` は明示的に有効化するまで false とする。
