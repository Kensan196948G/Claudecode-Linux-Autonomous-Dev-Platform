# ClaudeCode Native Linux Autonomous DevOS

## Purpose
Ubuntu native environmentでClaudeCodeを長時間運用し、複数プロジェクトの自律開発、監視、自己回復、記録を継続する。

## Core Policy
- Docs First
- Safe Execution
- Auto Healing
- 5-hour daily session
- 6-month project term

## Core Components
- systemd timer
- claude-safe
- memory guard
- recovery engine
- state.json

## Operating Notes
- ClaudeCodeは`claude-safe.sh`経由で起動する。
- `state.json`をClaudeの判断材料として毎セッションのプロンプトに合成する。
- OOM対策は「落とさない」より「OSを守って自動復帰する」を優先する。
- Dashboardは`web/app.py`で提供し、state/projects/log tailを確認する。
- Multi project schedulerはactive projectをpriority、weight、due dateで選定する。
