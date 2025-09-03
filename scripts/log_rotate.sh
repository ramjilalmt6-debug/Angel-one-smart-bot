#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
LOG="$HOME/angel-one-smart-bot/data/autopilot.out"
MAX=$((10*1024*1024))
[ -f "$LOG" ] || exit 0
sz=$(wc -c < "$LOG")
if [ "$sz" -ge "$MAX" ]; then
  mv "$LOG" "${LOG}.$(date +%Y%m%d-%H%M%S)"
  :> "$LOG"
  echo "rotated $LOG"
fi
