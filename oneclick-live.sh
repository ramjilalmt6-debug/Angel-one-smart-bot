#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="$HOME/angel-one-smart-bot"; ENV="$BASE/.env"; PREFIX="$PREFIX"
set -a; . "$ENV"; set +a
mkdir -p "$PREFIX/var/service"
[ -L "$PREFIX/var/service/crond" ] || { rm -rf "$PREFIX/var/service/crond"; ln -s "$PREFIX/etc/sv/crond" "$PREFIX/var/service/crond"; }
sv up crond >/dev/null 2>&1 || true
sed -i "s/^AUTO_SWITCH=.*/AUTO_SWITCH=1/" "$ENV"
sed -i "s/^DRY_RUN=.*/DRY_RUN=0/" "$ENV"
"$BASE/scripts/confirm_live.sh" || true
text="$("$BASE/scripts/state.sh")"
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" -d chat_id="${CHAT_ID}" --data-urlencode text="$text" >/dev/null || true
echo "[✓] LIVE trade enabled (guards active). Snapshot sent to Telegram."
