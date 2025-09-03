#!/usr/bin/env python3
from __future__ import annotations
import os
import subprocess
from pathlib import Path

# --- env load (.env se TELEGRAM_TOKEN / TELEGRAM_CHAT_ID / STRATEGY etc.) ---
try:
    from dotenv import load_dotenv
    load_dotenv(Path.home() / "angel-one-smart-bot" / ".env", override=True)
except Exception:
    pass

# --- best-effort notifier (agar scripts.notify available hai) ---
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send


root = Path.home() / "angel-one-smart-bot"

def main():
    # 1. state.sh run karke ek line status nikaalo
    res = subprocess.run(
        ["bash", "-lc", f"{root}/scripts/state.sh"],
        capture_output=True, text=True
    )
    out = (res.stdout or "").strip() or "STATE: (no output)"
    msg = "📟 Bot State\n" + out

    # 2. Try notify.send()
    ok = False
    try:
        ok = bool(send(msg))
    except Exception:
        ok = False
    print("sent:", ok)

    # 3. Agar notify fail ho jaye → curl fallback
    if not ok:
        tok = os.getenv("TELEGRAM_TOKEN", "")
        chat = os.getenv("TELEGRAM_CHAT_ID", "")
        if tok and chat:
            env = os.environ.copy()
            env["MSG"] = msg
            subprocess.run(
                ["bash", "-lc",
                 f'curl -s -X POST "https://api.telegram.org/bot{tok}/sendMessage" '
                 f'-d chat_id="{chat}" --data-urlencode text@- <<< "$MSG"'],
                check=False, env=env
            )
            print("fallback: curl send attempted")
        else:
            print("fallback skipped: missing TELEGRAM_TOKEN/CHAT")

if __name__ == "__main__":
    raise SystemExit(main())
