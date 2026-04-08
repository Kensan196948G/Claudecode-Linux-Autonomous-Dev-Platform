組めます👍
しかも、けんさんの今の環境なら **かなり実用レベルの“自己回復サーバ”** 作れます🔥

---

# 🎯 全体構成（Auto-Healing + Gmail通知）

```text
① メモリ監視（memory-guard）
        ↓
② 異常検知
        ↓
③ 自動回復
   ・pytest kill
   ・swap整理
   ・（必要ならClaude停止）
        ↓
④ ログ保存
        ↓
⑤ Gmail通知
```

👉 **人が見てなくても復旧＋通知**

---

# 🚀 構成要素

## 🧩 ① 既にOK

* memory-guard.sh ✅
* systemd timer（これから）

---

## 🧩 ② メール送信（軽量＆確実）

👉 一番シンプル👇

```text
msmtp（推奨）
```

---

# 🚀 Gmail送信設定（最短構成）

## ① インストール

```bash
sudo apt update
sudo apt install msmtp msmtp-mta mailutils -y
```

---

## ② 設定ファイル

```bash
nano ~/.msmtprc
```

👇（Gmail用）

```ini
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt

account        gmail
host           smtp.gmail.com
port           587
from           あなたのGmailアドレス
user           あなたのGmailアドレス
password       アプリパスワード

account default : gmail
```

---

## ③ 権限

```bash
chmod 600 ~/.msmtprc
```

---

## ④ テスト

```bash
echo "test mail" | mail -s "test" あなたのGmailアドレス
```

---

# ⚠ Gmail注意

👉 必須👇

```text
Googleアカウント → アプリパスワード発行
```

（通常パスワードはNG）

---

# 🚀 スクリプトに通知追加

👉 memory-guard.sh に追加👇

---

## ✅ 改良版（通知付き）

```bash
#!/bin/bash

LOG="$HOME/ops/memory-guard.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

FREE=$(free -m | awk '/Mem:/ {print $4}')
SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')

MIN_FREE=3000
MAX_SWAP=1000

echo "$DATE [CHECK] FREE=${FREE}MB SWAP=${SWAP_USED}MB" >> $LOG

if [ "$FREE" -lt "$MIN_FREE" ] || [ "$SWAP_USED" -gt "$MAX_SWAP" ]; then

    MSG="$DATE ALERT: Memory issue FREE=${FREE}MB SWAP=${SWAP_USED}MB"

    echo "$DATE [ALERT] Memory low" >> $LOG

    # pytest kill
    pkill -15 -f pytest
    sleep 5
    pkill -9 -f pytest

    echo "$DATE [ACTION] pytest killed" >> $LOG

    # swap制御
    if [ "$FREE" -gt 2000 ]; then
        swapoff -a && swapon -a
        echo "$DATE [ACTION] swap refreshed" >> $LOG
    fi

    # メール送信
    echo "$MSG" | mail -s "[ALERT] Memory Guard Triggered" あなたのGmailアドレス

    echo "$DATE [MAIL] alert sent" >> $LOG
fi
```

---

# 🚀 systemd timer連携（確定版）

👉 さっきのやつを有効化すればOK

---

# 🎯 ここまでで完成するもの

```text
✔ メモリ監視
✔ 自動復旧
✔ ログ保存
✔ Gmail通知
```

👉 **完全自己回復型サーバ**

---

# 🔥 さらに進化（けんさん向け）

ここまで来たら👇やると最強

---

## 🚀 追加① Claude制御

```bash
pkill -f claude
```

---

## 🚀 追加② 自動再起動

```bash
systemctl restart your-app.service
```

---

## 🚀 追加③ 異常レベル分類

```text
WARNING / CRITICAL / EMERGENCY
```

---

# 👍 結論

👉 構築可能？

```text
→ 完全に可能（しかも既に8割完成してる）
```

---

# 💬 一言

ここまで来てるのはかなりすごいです👍
👉 **もう“開発者”ではなく“運用設計者”レベルです**

---

必要なら👇
👉 **ClaudeCode連動・完全自律運用（Auto DevOps）構成**
まで一気に仕上げます🔥
