#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/angel-one-smart-bot"

# Stage everything that's not ignored
git add -A

# Commit only if there are staged changes
if ! git diff --cached --quiet; then
  git commit -m "Auto backup: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  git push
fi
