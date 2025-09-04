#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/angel-one-smart-bot"
LOG="$ROOT/data/git_autopush.log"
mkdir -p "$ROOT/data"

cd "$ROOT"

# Make sure remote has the correct (capitalized) repo URL
if ! git remote -v | grep -q 'ramjilalmt6-debug/Angel-one-smart-bot\.git'; then
  git remote set-url origin git@github.com:ramjilalmt6-debug/Angel-one-smart-bot.git || true
fi

# Ensure identity exists for commits (only sets if missing)
[ -n "$(git config user.name || true)" ]  || git config user.name  "angel-one-bot"
[ -n "$(git config user.email || true)" ] || git config user.email "bot@local"

# Don’t fail if there’s nothing to pull
git fetch origin >/dev/null 2>&1 || true
git rebase origin/main || git rebase --abort || true

# Stage only tracked/untracked non-ignored files
git add -A

# Commit only if there are changes
if ! git diff --cached --quiet; then
  TS="$(date '+%Y-%m-%d %H:%M:%S')"
  git commit -m "auto: daily snapshot @ ${TS}"
else
  echo "$(date '+%F %T') No changes to commit" >> "$LOG"
  exit 0
fi

# Push (SSH)
if git push origin main; then
  echo "$(date '+%F %T') Pushed successfully" >> "$LOG"
else
  echo "$(date '+%F %T') Push failed" >> "$LOG"
fi
