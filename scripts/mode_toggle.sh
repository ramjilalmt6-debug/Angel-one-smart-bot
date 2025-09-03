#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ENV="$HOME/angel-one-smart-bot/.env"
key="$1"; val="$2"
tmp="$(mktemp)"
awk -vK="$key" -vV="$val" 'BEGIN{f=0} $0~("^"K"="){print K"="V; f=1; next} {print} END{if(!f)print K"="V}' "$ENV" > "$tmp"
mv "$tmp" "$ENV"; chmod 600 "$ENV"
echo "Set $key=$val"
