#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
BK="$ROOT/data/crontab.backup"

if [ ! -s "$BK" ]; then
  echo "Backup missing or empty: $BK"; exit 1
fi

# Keep a rollback point
NOW=$(date +%s)
crontab -l 2>/dev/null > "$ROOT/data/crontab.pre.$NOW" || true

# Load backup
crontab "$BK"

echo "Restored crontab from $BK"
crontab -l | sed -n '1,200p'
