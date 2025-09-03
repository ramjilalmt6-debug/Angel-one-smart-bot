#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
DATA="$HOME/angel-one-smart-bot/data"; mkdir -p "$DATA"
TS=$(date +%s)
cat > "$DATA/confirm_live.json" <<JSON
{ "strategy":"pcr_momentum_oi", "ts": $TS, "reason":"guards green", "risk_ok": true }
JSON
python "$HOME/angel-one-smart-bot/scripts/switch_guard.py"
