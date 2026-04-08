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
- `ci.repair_attempt_limit` は15以下にする。
- `ci.stable` は test / lint / build / CI / review / security / error 0 の判定を満たした場合のみ true とする。
- `decision.next_action` は `idle`, `develop`, `verify`, `repair_ci`, `cooldown`, `suspend` の範囲にする。
- `github.auto_merge_enabled` と `ci.auto_merge_enabled` は明示的に有効化するまで false とする。
