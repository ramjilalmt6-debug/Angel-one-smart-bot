#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$HOME/angel-one-smart-bot"
ENV="$ROOT/.env"
mkdir -p "$ROOT"; touch "$ENV"

set_kv() {
  k="$1"; v="$2"
  if grep -q "^$k=" "$ENV" 2>/dev/null; then
    sed -i "s|^$k=.*|$k=$v|" "$ENV"
  else
    echo "$k=$v" >> "$ENV"
  fi
}

get_or_prompt() {
  local key="$1" prompt="$2" secret="${3:-}"
  local cur="$(grep -E "^$key=" "$ENV" 2>/dev/null | sed -n "s/^$key=//p")"
  if [ -n "$cur" ]; then
    echo "$key already set."
    return
  fi
  if [ -n "$secret" ]; then
    read -rsp "$prompt: " val; echo
  else
    read -rp "$prompt: " val
  fi
  [ -z "$val" ] && { echo "Skipped $key (empty)"; return; }
  set_kv "$key" "$val"
}

echo ">> Setting SmartAPI credentials in $ENV"
get_or_prompt API_KEY       "Enter API_KEY"
get_or_prompt CLIENT_CODE   "Enter CLIENT_CODE"
get_or_prompt MPIN          "Enter MPIN" "secret"
get_or_prompt TOTP_SECRET   "Enter TOTP_SECRET (base32 from Authenticator)" "secret"

chmod 600 "$ENV"
echo "Done. Current keys:"
grep -E '^(API_KEY|CLIENT_CODE|MPIN|TOTP_SECRET)=' "$ENV" | sed 's/=.*/=****/'

# Optional quick OTP sanity check (does not send to server)
if python - <<'PY' 2>/dev/null; then :; fi
import os, sys
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path.home()/ "angel-one-smart-bot"/ ".env", override=True)
except Exception:
    pass
sec = os.getenv("TOTP_SECRET","")
if not sec:
    print("TOTP sanity: missing")
    sys.exit(0)
try:
    import pyotp
    print("TOTP sanity: looks OK (example OTP:", pyotp.TOTP(sec).now(), ")")
except Exception as e:
    print("TOTP sanity: pyotp not available or bad secret:", e)
PY
