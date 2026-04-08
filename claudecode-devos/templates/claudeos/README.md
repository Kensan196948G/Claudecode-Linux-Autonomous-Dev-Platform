# ClaudeOS Template Source

`claudecode-devos/templates/claudeos` は DevOS から起動する Claude の正規テンプレートです。

Claude 実行前に `sync-claudeos-template.sh` が対象リポジトリまたはWorkTreeの `.claude/claudeos` へ同期します。
agents、skills、commands、rules、hooks、scripts、contexts、examples、mcp-configs、system、loops、ci、evolution、worktree はこのディレクトリを基準にしてください。

同期に失敗した場合、完全自立型開発セッションはBlocked扱いで停止します。
