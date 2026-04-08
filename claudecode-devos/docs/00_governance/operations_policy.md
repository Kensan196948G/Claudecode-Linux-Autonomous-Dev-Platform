# 運用ポリシー

1. ClaudeCodeは常に`claude-safe.sh`経由で起動する。
2. 直接`claude --dangerously-skip-permissions`を常時実行しない。
3. 1セッションの最大実行時間は5時間とする。
4. OOM・高負荷時はrecoveryを優先する。
5. Docs更新をコード変更と同等に扱う。
6. プロジェクト登録日から6か月後をリリース目標とする。
7. `state.json`は実行状態のSingle Source of Truthとして扱う。
