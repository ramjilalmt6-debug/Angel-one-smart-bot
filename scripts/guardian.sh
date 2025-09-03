#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/angel-one-smart-bot"
LOG="$ROOT/data/autopilot.out"
PY="$ROOT/venv/bin/python"

mkdir -p "$ROOT/data"

# venv best-effort
. "$ROOT/venv/bin/activate" 2>/dev/null || true

# already running?
if pgrep -af "scripts/autopilot.py" >/dev/null; then
  exit 0
fi

# ensure project root on sys.path for dynamic imports
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# start
echo '{"event":"guardian_start"}' >> "$LOG"
# Use setsid so it detaches even inside cron/Termux
setsid "$PY" -u "$ROOT/scripts/autopilot.py" >> "$LOG" 2>&1 &
disown || true
sleep 3

# report
if pgrep -af "scripts/autopilot.py" >/dev/null; then
  echo '{"event":"guardian_ok"}' >> "$LOG"
else
  echo '{"event":"guardian_fail"}' >> "$LOG"
fi
