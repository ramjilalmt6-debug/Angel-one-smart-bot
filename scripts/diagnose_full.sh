#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
SCR="$ROOT/scripts"
DATA="$ROOT/data"
ENVF="$ROOT/.env"
LOG="$DATA/autopilot.out"
OUT="$DATA/diag_full_$(date +%F_%H%M%S).log"

hr(){ printf '\n%s\n' "============================================================"; }
shh(){ "$@" 2>/dev/null || true; }
say(){ printf '%s\n' "$@" | tee -a "$OUT"; }
mask(){ awk -F= 'BEGIN{OFS="="} $1~/(_KEY|SECRET|TOKEN|MPIN|PASSWORD|CHAT_ID)$/ { if(length($2)>8){ sub(/.*/,substr($2,1,3)"***"substr($2,length($2)-2),$2) } } {print $0}' ; }

: > "$OUT"
hr; say "ANGEL ONE SMART BOT — FULL DIAG $(date '+%F %T %Z')"
say "Device: $(uname -a)"
say "User  : $(whoami)  | Shell: $SHELL"
say "Dir   : $ROOT"

# 1) Python / venv
hr; say "[1/10] Python & venv"
say "python3: $(python3 -V 2>&1)"
if [ -x "$ROOT/venv/bin/python" ]; then
  say "venv   : present ($( "$ROOT/venv/bin/python" -V 2>&1))"
else
  say "venv   : not found (ok, not mandatory)"
fi

# 2) Git status
hr; say "[2/10] Git"
if [ -d "$ROOT/.git" ]; then
  (cd "$ROOT"
    say "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo n/a)"
    say "remote: $(git remote -v | head -n1 || echo 'none')"
    say "dirty? : $( git diff --quiet && echo clean || echo 'changes pending')"
    say "HEAD  : $(git rev-parse --short HEAD 2>/dev/null || echo n/a)"
  ) | tee -a "$OUT"
else
  say "repo  : not a git repo"
fi

# 3) .env sanity (masked)
hr; say "[3/10] .env keys (masked)"
if [ -f "$ENVF" ]; then
  sed -n '1,200p' "$ENVF" | mask | tee -a "$OUT" >/dev/null
  need=(API_KEY CLIENT_CODE MPIN TOTP_SECRET TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID STRATEGY TREND_EXCHANGE TREND_SYMBOLTOKEN TREND_INTERVAL TREND_LOOKBACK_MIN TREND_ADX_TREND TREND_ADX_RANGE)
  miss=()
  for k in "${need[@]}"; do grep -q "^$k=" "$ENVF" || miss+=("$k"); done
  if [ "${#miss[@]}" -gt 0 ]; then say "MISSING: ${miss[*]}"; else say "All required keys present ✅"; fi
else
  say ".env missing ❌"
fi

# 4) Network preflight
hr; say "[4/10] Network preflight"
if [ -x "$SCR/net_preflight.sh" ]; then
  R="$(bash -lc "$SCR/net_preflight.sh" || true)"; say "$R"
else
  # quick inline DNS/TCP check
  PYDNS='import socket;print(socket.gethostbyname("apiconnect.angelone.in"))'
  IP="$(python3 - <<PY
$PYDNS
PY
  2>/dev/null || true)"
  if [ -n "$IP" ]; then say "DNS ok: apiconnect.angelone.in -> $IP"; else say "DNS fail ❌"; fi
  (timeout 5 bash -lc "exec 3<>/dev/tcp/${IP:-1.1.1.1}/443" && say "TCP/443 ok") || say "TCP/443 fail ❌"
fi

# 5) Telegram connectivity (dry ping only if DIAG_PING=1)
hr; say "[5/10] Telegram notify bridge"
if [ -f "$SCR/notify.py" ]; then
  if [ "${DIAG_PING:-0}" = "1" ]; then
    say "Sending test…"; R="$(python3 "$SCR/notify.py" 2>/dev/null || true)"; say "$R"
  else
    say "notify.py present. (Set DIAG_PING=1 to send a test.)"
  fi
else
  say "notify.py missing ❌"
fi

# 6) Cron overview (key jobs)
hr; say "[6/10] Cron entries (grep)"
( crontab -l 2>/dev/null | sed -n '1,200p' ) | tee -a "$OUT" >/dev/null
say "-- must-have checks --"
for pat in guardian.sh trend_autoswitch.py health_sentinel.py alert_watch.py daily_alive_ping.py git_autopush.sh; do
  crontab -l 2>/dev/null | grep -q "$pat" && say "✓ $pat" || say "✗ $pat"
done

# 7) Processes
hr; say "[7/10] Processes"
pgrep -fl 'autopilot.py' >/dev/null && pgrep -fl 'autopilot.py' | tee -a "$OUT" || say "autopilot.py not running"
pgrep -fl 'python.*alert_watch.py' >/dev/null && pgrep -fl 'alert_watch.py' | tee -a "$OUT" || true

# 8) Trend tools quick check
hr; say "[8/10] Trend check"
if [ -x "$SCR/trend_check.py" ]; then
  say "$(bash -lc "$SCR/trend_check.py" 2>/dev/null || echo 'trend_check.py failed')"
else
  say "trend_check.py missing (ok if not used)"
fi
if [ -x "$SCR/trend_autoswitch.py" ]; then
  say "$(bash -lc "$SCR/trend_autoswitch.py" 2>/dev/null || echo 'trend_autoswitch.py failed')"
else
  say "trend_autoswitch.py missing (ok if not used)"
fi

# 9) SmartAPI token path (if helper exists)
hr; say "[9/10] SmartAPI token check"
if [ -x "$SCR/smartapi_token_check.py" ]; then
  say "$(bash -lc "$SCR/smartapi_token_check.py" 2>/dev/null || echo 'smartapi_token_check failed')"
else
  say "smartapi_token_check.py not found (skip)"
fi

# 10) Logs snapshot
hr; say "[10/10] Logs snapshot"
[ -f "$LOG" ] && say "autopilot.out size: $(wc -c < "$LOG") bytes" || say "autopilot.out not found"
say "--- last 40 lines ---"
[ -f "$LOG" ] && tail -n 40 "$LOG" | tee -a "$OUT" >/dev/null || true

hr; say "Report saved → $OUT"
