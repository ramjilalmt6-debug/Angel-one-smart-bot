#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
echo "=== ACTIVE CRON ==="
crontab -l | sed -n '1,200p'
echo
echo "=== MUST-HAVE ENTRIES (grep) ==="
crontab -l | grep -E 'guardian\.sh|trend_autoswitch\.py|health_sentinel\.py|positions_to_pnl\.py' || true
echo
echo "=== Guardian status ==="
pgrep -af "scripts/guardian.sh" || echo "(guardian not running via cron — ok)"
pgrep -af "scripts/autopilot.py" || echo "(autopilot not running)"
echo
echo "=== Tail autopilot.out ==="
tail -n 30 "$ROOT/data/autopilot.out" || true
