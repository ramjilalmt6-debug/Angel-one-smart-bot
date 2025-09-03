#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
STR="${1:-pcr_momentum_oi}"
sed -i "s/^STRATEGY=.*/STRATEGY=$STR/" "$ROOT/.env"
:> "$ROOT/data/autopilot.out"
pkill -f "python3 .*scripts/autopilot.py" 2>/dev/null || true
bash -lc "$ROOT/scripts/guardian.sh"
echo "Switched strategy to $STR"
