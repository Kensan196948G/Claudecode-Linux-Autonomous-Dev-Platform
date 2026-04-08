# 進化フラグメントレビューガイド

## 概要

`evolution_loop.py` が生成する「進化フラグメント」（プロンプト改善・最適化提案）は
`runtime/evolution/history/` に差分として記録される。
このガイドは記録フォーマット・レビュー手順・ロールバック方法を定義する。

## 記録フォーマット

ファイル名: `runtime/evolution/history/frag_YYYYMMDD_HHMMSS.json`

```json
{
  "generated_at": "YYYY-MM-DD HH:MM:SS",
  "cycle_id": "<uuid>",
  "source": "evolution_loop",
  "decision": { ... },
  "prompt_fragment": "...",
  "before_hash": "<sha256 of prompt before>",
  "after_hash": "<sha256 of prompt after>",
  "approved": null,
  "approved_by": null,
  "approved_at": null
}
```

`approved` フィールド:
- `null` — 未レビュー
- `true` — 採用済み
- `false` — 却下済み

## 記録のタイミング

`evolution_loop.py:run_evolution_cycle()` の `finally` ブロックで
`record_evolution_fragment(detail)` を呼ぶ。

実装: `claudecode-devos/core/evolution_loop.py` に追加済み（下記参照）。

## レビュー手順

### 1. 未レビューフラグメントの確認

```bash
python3 claudecode-devos/ops/state_manager.py get evolution.last_cycle_at
ls claudecode-devos/runtime/evolution/history/ | tail -10
```

### 2. フラグメント内容の確認

```bash
cat claudecode-devos/runtime/evolution/history/frag_YYYYMMDD_HHMMSS.json | python3 -m json.tool
```

### 3. 採用・却下の記録

```bash
# 採用
python3 - <<EOF
import json; from pathlib import Path
f = Path('runtime/evolution/history/frag_YYYYMMDD_HHMMSS.json')
d = json.loads(f.read_text()); d['approved'] = True; d['approved_by'] = 'EvolutionManager'
import datetime; d['approved_at'] = str(datetime.datetime.now())[:19]
f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
EOF
```

### 4. ロールバック

フラグメントが採用済みでシステムが不安定な場合:

1. `approved: false` に更新
2. `before_hash` で元のプロンプトを特定
3. `git revert` または手動でプロンプトファイルを復元
4. `state.json` の `evolution.last_cycle_detail` を前サイクル値に戻す

## 自動レビューゲート

`codex_review_status` が `failure` の場合は進化フラグメントを自動却下:

```
evolution_loop.py → record_fragment() → check codex_review_status
  → if failure: approved = false, reason = "codex_review_blocked"
```

## 保持ポリシー

- `approved: true` — 永続保持
- `approved: false` — 30日後に `runtime/evolution/archive/` へ移動
- `approved: null` — 7日後に自動却下（自動レビューゲートが処理）

`.gitignore` により `runtime/evolution/history/*` は Git 管理外。
定期バックアップが必要な場合は `runtime/archive/` に圧縮コピーを保存する。
