#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$HOME/angel-one-smart-bot"
S="$ROOT/scripts"
D="$ROOT/data"
LOG="$D/diag.log"

mkdir -p "$D"
pyv=$(python3 -V 2>/dev/null | awk "{print \$2}")
venv_ok=no; [ -d "$ROOT/venv" ] || [ -d "$ROOT/.venv" ] && venv_ok=yes
curip=$(curl -sS ifconfig.me || true)
ap="$ROOT/scripts/autopilot.py"
ap_ok=no; pgrep -f "$ap" >/dev/null 2>&1 && ap_ok=yes
ts=$(date +%Y-%m-%d
