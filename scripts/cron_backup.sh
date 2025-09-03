#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
BKP="$ROOT/data/crontab.backup"

mkdir -p "$ROOT/data"
crontab -l > "$BKP" 2>/dev/null || true
echo "[✓] Crontab backed up to $BKP"
