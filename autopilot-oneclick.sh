#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="$HOME/angel-one-smart-bot"; ENV="$BASE/.env"
set -a; . "$ENV"; set +a
mkdir -p "$PREFIX/var/service"
[ -e "$PREFIX/var/service/crond" ] && [ ! -L "$PREFIX/var/service/crond" ] && rm -rf "$PREFIX/var/service/crond" || true
ln -sf "$PREFIX/etc/sv/crond" "$PREFIX/var/service/crond" 2>/dev/null || true
sv up crond >/dev/null 2>&1 || true
sed -i "s/^AUTO_SWITCH=.*/AUTO_SWITCH=1/" "$ENV" || echo AUTO_SWITCH=1 >> "$ENV"
sed -i "s/^DRY_RUN=.*/DRY_RUN=0/" "$ENV"      || echo DRY_RUN=0 >> "$ENV"
grep -q "^STRATEGY_MODULE=" "$ENV" || echo "STRATEGY_MODULE=strategies.pcr_momentum_oi" >> "$ENV"
TMP=$(mktemp); crontab -l 2>/dev/null > "$TMP" || true
L1="* 9-15 * * 1-5 cd \$HOME/angel-one-smart-bot && set -a;. ./.env;set +a; python3 scripts/risk_guard.py >> data/risk.log 2>&1"
grep -Fq "$L1" "$TMP" || echo "$L1" >> "$TMP"
L2="* 9-15 * * 1-5 cd \$HOME/angel-one-smart-bot && set -a;. ./.env;set +a; python3 scripts/switch_guard.py >> data/guard.log 2>&1"
grep -Fq "$L2" "$TMP" || echo "$L2" >> "$TMP"
L3="* 9-15 * * 1-5 cd \$HOME/angel-one-smart-bot && set -a;. ./.env;set +a; python3 scripts/autopilot.py >> data/strategy.log 2>&1"
grep -Fq "$L3" "$TMP" || echo "$L3" >> "$TMP"
L4="*/30 9-15 * * 1-5 set -a;. \$HOME/angel-one-smart-bot/.env;set +a; text=\$(\$HOME/angel-one-smart-bot/scripts/state.sh); curl -s -X POST \"https://api.telegram.org/bot\${BOT_TOKEN}/sendMessage\" -d chat_id=\"\${CHAT_ID}\" --data-urlencode text=\"\$text\" >/dev/null"
grep -Fq "$L4" "$TMP" || echo "$L4" >> "$TMP"
L5="0 9 * * 1-5 \$HOME/angel-one-smart-bot/scripts/health_check.sh >> \$HOME/angel-one-smart-bot/data/health.log 2>&1"
grep -Fq "$L5" "$TMP" || echo "$L5" >> "$TMP"
L6="0 18 * * 1-5 find \$HOME/angel-one-smart-bot/data -type f -name '*.log' -size +2M -exec truncate -s 0 {} \;"
grep -Fq "$L6" "$TMP" || echo "$L6" >> "$TMP"
L7="* 9-15 * * 1-5 cd \$HOME/angel-one-smart-bot && set -a;. ./.env;set +a; [ \"\$SQUAREOFF_ON_KILL\" = \"1\" ] && [ \"\$DRY_RUN\" = \"1\" ] && python3 scripts/squareoff_all.py >> data/squareoff.log 2>&1"
grep -Fq "$L7" "$TMP" || echo "$L7" >> "$TMP"
crontab "$TMP"; rm -f "$TMP"
"$BASE/scripts/confirm_live.sh" || true
text="$("$BASE/scripts/state.sh")"
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" -d chat_id="${CHAT_ID}" --data-urlencode text="$text" >/dev/null || true
echo "[✓] Autopilot armed: LIVE + cron guards + strategy loop. Snapshot sent to Telegram."
