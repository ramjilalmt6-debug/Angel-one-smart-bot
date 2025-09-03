#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
LOG="$ROOT/data/net-fix.log"
DEDICATED_IP="${DEDICATED_IP:-89.117.176.75}"
RECONNECT_CMD="${RECONNECT_CMD:-}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
say(){ echo "[$(ts)] $*"; }

{
  say "[net-fix] start"
  CUR_IP="$(curl -sS --max-time 6 https://api.ipify.org || true)"
  say "current_ip=$CUR_IP expect=$DEDICATED_IP"
  if [ "$CUR_IP" != "$DEDICATED_IP" ]; then
    say "IP mismatch -> reconnect"
    if [ -n "$RECONNECT_CMD" ]; then
      bash -lc "$RECONNECT_CMD" || true
    else
      if command -v nordvpn >/dev/null 2>&1; then
        nordvpn c || true
      elif command -v wg-quick >/dev/null 2>&1; then
        wg-quick down wg0 || true
        sleep 1
        wg-quick up wg0 || true
      fi
    fi
    sleep 4
    CUR_IP="$(curl -sS --max-time 6 https://api.ipify.org || true)"
    say "post-reconnect ip=$CUR_IP"
  else
    say "IP ok"
  fi
  say "[net-fix] done"
} >>"$LOG" 2>&1
