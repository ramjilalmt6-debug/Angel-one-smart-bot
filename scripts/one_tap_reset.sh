#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
# LIVE ON, DRY OFF
sed -i 's/^LIVE=.*/LIVE=1/' "$ROOT/.env"
sed -i 's/^DRY=.*/DRY=0/'   "$ROOT/.env"
# guardian restart (autopilot up)
bash -lc "$ROOT/scripts/guardian.sh"
# fresh PnL pull
"$ROOT/venv/bin/python" -u "$ROOT/scripts/positions_to_pnl.py" >> "$ROOT/data/autopilot.out" 2>&1 || true
# state to Telegram
bash -lc "$ROOT/scripts/state_push.py" || true
echo "One-tap reset done."
