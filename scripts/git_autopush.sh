#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/angel-one-smart-bot"
LOG="$ROOT/data/git_autopush.log"

mkdir -p "$ROOT" "$ROOT/data"
cd "$ROOT"

# pull safely (don’t break on local changes)
git pull --rebase --autostash || true

# stage & commit only if there are changes (working tree or index)
if ! git diff --quiet --exit-code || ! git diff --cached --quiet --exit-code; then
  git add -A
  git commit -m "auto: snapshot @ $(date '+%F %T')" || true
fi

# push with notification on failure
if git push origin main; then
  echo "$(date '+%F %T') Pushed successfully" >> "$LOG"
else
  echo "$(date '+%F %T') Push failed" >> "$LOG"
  # send a Telegram alert using notify.send(...)
  python3 - <<'PY' >/dev/null 2>&1 || true
from pathlib import Path
import importlib.util
ROOT = Path.home() / "angel-one-smart-bot"
spec = importlib.util.spec_from_file_location("notify", str(ROOT/"scripts"/"notify.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.send("⚠️ Git autopush failed on device")
PY
  exit 1
fi
