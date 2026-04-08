# LOOP_CONTROL

## ループコマンド

```text
/loop 30m ClaudeOS Monitor
/loop 2h ClaudeOS Development
/loop 1h ClaudeOS Verify
/loop 1h ClaudeOS Improvement
```

## 条件

- 3回連続で成功した場合のみ、安定状態（STABLE）と判定します。
- 安定状態に到達した場合は、必要に応じてPRを作成できます。
- マージはCIがGreenで、かつマージポリシーが許可している場合のみ実行します。
- STABLE未達の場合は、PR作成は可能でもmerge/deployは禁止します。
- エラー発生時はRepairモードへ切り替えます。
- 自動修復は最大15回までとし、リトライ上限に達した時点で停止します。
- base branchへ直接pushしてはいけません。
- 自動開発セッションの最大作業時間は5時間です。5時間を超えて作業を継続してはいけません。
- 5時間に到達する前に、作業整理、最小commit、push、Draft PR作成、検証結果、残課題、再開ポイントの記録を完了してください。
