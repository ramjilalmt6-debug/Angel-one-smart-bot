#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
LOG="$ROOT/data/update-instruments.log"

# Pick correct venv Python
if [ -x "$ROOT/venv/bin/python" ]; then
  PYTHON="$ROOT/venv/bin/python"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  # Fallback (will likely miss smartapi if not installed globally)
  PYTHON="$(command -v python3)"
fi

ts() { date "+%Y-%m-%d %H:%M:%S"; }

{
  echo "[$(ts)] === instruments update start ==="
  echo "[$(ts)] Using interpreter: $PYTHON"
  # Export env from .env if present
  set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a

  "$PYTHON" "$ROOT/scripts/update_instruments.py"
  echo "[$(ts)] done."
} >>"$LOG" 2>&1
