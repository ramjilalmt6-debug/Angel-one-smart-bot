#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
DST="$ROOT/data/backups"
mkdir -p "$DST" "$ROOT/data/logs" 2>/dev/null || true
tar -czf "$DST/auto-$(date +%Y%m%d).tgz" -C "$ROOT" .env data >/dev/null 2>&1 || true
echo "backup ok: $DST"
