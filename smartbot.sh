#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="$HOME/angel-one-smart-bot"
ENV="$BASE/.env"
set -a; . "$ENV"; set +a
cmd="${1:-menu}"
case "$cmd" in
  health)   "$BASE/scripts/health_check.sh" ;;
  status)   "$BASE/scripts/state.sh" ;;
  go-live)  "$BASE/scripts/confirm_live.sh" ;;
  go-dry)   sed -i "s/^DRY_RUN=.*/DRY_RUN=1/" "$ENV"; "$BASE/scripts/state.sh" ;;
  squareoff-now) FORCE_SQUAREOFF=1 python3 "$BASE/scripts/squareoff_all.py" ;;
  auto-on)  sed -i "s/^AUTO_SWITCH=.*/AUTO_SWITCH=1/" "$ENV"; echo "[✓] AUTO_SWITCH=1" ;;
  auto-off) sed -i "s/^AUTO_SWITCH=.*/AUTO_SWITCH=0/" "$ENV"; echo "[✓] AUTO_SWITCH=0" ;;
  snapshot) text="$("$BASE/scripts/state.sh")"; curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" -d chat_id="${CHAT_ID}" --data-urlencode text="$text" >/dev/null && echo "[✓] Snapshot sent to Telegram" || echo "[X] Telegram send failed" ;;
  *) echo "Usage: smartbot.sh [health|status|go-live|go-dry|squareoff-now|auto-on|auto-off|snapshot]";;
esac
