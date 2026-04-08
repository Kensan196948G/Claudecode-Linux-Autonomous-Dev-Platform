# ClaudeOS Native Session Start

## LOOP_COMMANDS

/loop 30m ClaudeOS Monitor
/loop 2h ClaudeOS Development
/loop 1h ClaudeOS Verify
/loop 1h ClaudeOS Improvement

## PROMPT_BODY

以下を順番に実行してください。

1. Docsフォルダを確認
2. state.jsonの最新状態を確認
3. 前回セッションの残課題を確認
4. Git状態、Issue、CI状態を確認
5. Monitorフェーズから開始
6. Development -> Verify -> Improvementを実行
7. 変更した内容をDocsに反映
8. セッション終了時にdaily reportを更新

## RULES

- 実行は常にsafe modeを優先
- 高負荷時は並列数を減らす
- メモリ圧迫時は軽量実行へ移行
- DocsをSingle Source of Truthとする
