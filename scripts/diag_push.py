#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path.home()/ "angel-one-smart-bot"/ ".env", override=True)
except Exception:
    pass
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send

root = Path.home()/ "angel-one-smart-bot"
p = subprocess.run(["python3", str(root/"scripts"/"diagnose_full.py")],
                   capture_output=True, text=True)
out = p.stdout.strip() or "(no output)"
out = out[-3500:]  # Telegram size-safe
ok = send("🩺 Autopilot Daily Diagnostic (08:55 IST)\n\n" + out)
print("sent:", ok)
if not ok:
    import os, subprocess
    tok=os.getenv("TELEGRAM_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if tok and chat:
        msg="🩺 Autopilot Daily Diagnostic (curl fallback)\n\n"+out
        env = os.environ.copy(); env["MSG"] = msg
        subprocess.run([
            "bash","-lc",
            f'curl -s -X POST "https://api.telegram.org/bot{tok}/sendMessage" -d chat_id="{chat}" --data-urlencode text@- <<< "$MSG"'
        ], check=False, env=env)
        print("fallback: curl send attempted")
    else:
        print("fallback skipped: missing TELEGRAM_TOKEN/CHAT")

