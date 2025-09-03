#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
. "$ROOT/venv/bin/activate" 2>/dev/null || true
python -u "$ROOT/scripts/square_off_all.py" >> "$ROOT/data/autopilot.out" 2>&1
