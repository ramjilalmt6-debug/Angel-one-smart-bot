#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
ENV="$ROOT/.env"
. "$ENV" 2>/dev/null || true
MODE=$([ "${LIVE:-0}" = "1" ] && [ "${DRY:-1}" = "0" ] && echo LIVE || echo DRY)
STRAT="${STRATEGY:-pcr_momentum_oi}"
PNL_FILE="$ROOT/data/pnl.json"
PNL=$( [ -f "$PNL_FILE" ] && jq -r '.pnl' "$PNL_FILE" 2>/dev/null || echo "NA")
TS=$(  [ -f "$PNL_FILE" ] && date -d @$(jq -r '.ts//empty' "$PNL_FILE" 2>/dev/null) '+%H:%M:%S' 2>/dev/null || echo "-" )
PID=$(pgrep -af "python3 .*scripts/autopilot.py" | awk '{print $1}' | head -n1)
PID=${PID:-"-"}
echo "MODE=$MODE | STRATEGY=$STRAT | PnL=$PNL (ts:$TS) | PID=$PID"
