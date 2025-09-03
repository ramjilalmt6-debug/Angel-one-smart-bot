#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ENV="$HOME/angel-one-smart-bot/.env"
LOGDIR="$HOME/angel-one-smart-bot/data"
LOG="$LOGDIR/health.log"
mkdir -p "$LOGDIR"

# Load env
[[ -f "$ENV" ]] || { echo "[X] .env not found at $ENV" | tee -a "$LOG"; exit 1; }
set -a; . "$ENV"; set +a

{
  echo "== Angel One Smart Bot :: Health Check =="
  date

  # 1) External IP
  MYIP="$(curl -s https://ifconfig.me || true)"
  echo "[i] External IP: $MYIP"

  # 2) VPN lock
  if [[ -n "${NORDVPN_REQUIRED_IP:-}" && "$MYIP" == "$NORDVPN_REQUIRED_IP" ]]; then
    echo "[✓] VPN IP lock OK ($MYIP)"
  else
    echo "[X] VPN IP mismatch! Expected $NORDVPN_REQUIRED_IP but got $MYIP"
  fi

  # 3) Telegram ping
  if [[ -n "${BOT_TOKEN:-}" && -n "${CHAT_ID:-}" ]]; then
    MSG="✅ Bot health-check OK at $(date '+%Y-%m-%d %H:%M:%S') (IP: $MYIP)"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
         -d chat_id="$CHAT_ID" -d text="$MSG" >/dev/null \
      && echo "[✓] Telegram ping sent" || echo "[X] Telegram ping failed"
  else
    echo "[X] Telegram creds missing"
  fi

  # 4) TOTP sanity with dynamic Base32 padding + optional OTP preview
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' || true
import os, re, base64
secret = os.getenv("TOTP_SECRET","").strip().replace(" ","").upper()
if not secret:
    print("[i] TOTP_SECRET missing; skip")
else:
    if not re.fullmatch(r'[A-Z2-7]+', secret):
        print("[X] TOTP secret has invalid characters; expected only A-Z and 2-7")
    else:
        pad = (-len(secret)) % 8
        try:
            base64.b32decode(secret + "="*pad, casefold=True)
            try:
                import pyotp
                otp = pyotp.TOTP(secret).now()
                print(f"[✓] TOTP secret OK. Current OTP: {otp}")
            except Exception:
                print("[✓] TOTP secret OK (base32). Install pyotp to preview codes: pip install pyotp")
        except Exception as e:
            print("[X] TOTP secret invalid:", e)
PY
  else
    echo "[i] Python not found; skipping TOTP sanity"
  fi

  echo "== Health-check complete =="
} | tee -a "$LOG"
