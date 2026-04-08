# dangerously_skip_permissions 使用規則

## 原則

`dangerously_skip_permissions: true` は **デフォルト禁止**。
許可されていない状況で使用した場合は即時 Blocked 扱いとする。

## 使用が許可される条件（すべてを満たすこと）

1. **隔離環境**
   - Docker コンテナ / VM / CI ランナー のいずれかで実行中
   - 本番データへのアクセス経路が完全に遮断されている

2. **明示的な事前承認**
   - GitHub Issue または PR コメントに `[ALLOW_SKIP_PERMISSIONS]` タグがある
   - CTO ロールが承認コメントを残している

3. **スコープが限定的**
   - 操作対象がリポジトリ内の特定サブディレクトリのみ
   - `rm -rf /`, ネットワーク送信, 秘密情報アクセスを含まない

4. **ロールバック手段が確保されている**
   - git commit 済みの差分がある（作業が追跡可能）

## 使用が禁止される状況

- ホスト OS 上での直接実行
- `DEVOS_HOME` が `/opt/claudecode-devos` を指している本番環境
- CI 修復ループ中（Auto Repair は通常権限で完結させる）
- セキュリティ脆弱性の修正中（潜在的影響範囲が不明のため）

## 設定方法

`.claude/settings.json` の `permissions.allow` を変更するのではなく、
`--dangerously-skip-permissions` フラグを CLI 起動時に限定使用する。

```bash
# 正しい使用例（CI スクリプト内のみ）
claude --dangerously-skip-permissions --print "lint fix" 2>&1
```

設定ファイルへの常設追加は **禁止**。

## 監査証跡

使用した場合は以下を記録する:

```json
{
  "dangerously_skip_permissions": {
    "used_at": "YYYY-MM-DD HH:MM:SS",
    "reason": "...",
    "environment": "docker|vm|ci",
    "approver": "github-issue#NNN or PR#NNN",
    "scope": "path/to/directory"
  }
}
```

記録先: `runtime/decisions/permission_overrides.log`
