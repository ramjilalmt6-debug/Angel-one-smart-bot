#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ok(){ echo "{\"event\":\"net_preflight_ok\",\"ms\":$1,\"detail\":\"ok\"}"; exit 0; }
fail(){ echo "{\"event\":\"net_preflight_fail\",\"why\":\"$1\"}"; exit 1; }

HOST="apiconnect.angelone.in"
PORT=443
t0=$(date +%s%3N)

# --- DNS (Python-based, Termux-friendly) ---
IP="$(python3 - <<'PY'
import socket, sys
host = "apiconnect.angelone.in"
try:
    ip = socket.gethostbyname(host)
    print(ip)
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
)" || fail "dns"

# --- TCP/443 reachability (no SNI needed) ---
# use resolved IP so DNS isn’t required twice
timeout 6 bash -lc "exec 3<>/dev/tcp/${IP}/$PORT" 2>/dev/null || fail "tcp"
exec 3<&- 3>&-

# --- Lightweight HTTPS HEAD (optional) ---
if command -v curl >/dev/null 2>&1; then
  curl -sS --max-time 8 -I "https://${HOST}/" >/dev/null || fail "https"
fi

t1=$(date +%s%3N); ok $((t1 - t0))
