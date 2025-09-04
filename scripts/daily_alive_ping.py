#!/usr/bin/env python3
import os, subprocess, datetime, importlib.util
from pathlib import Path

ROOT = Path.home()/ "angel-one-smart-bot"
# Load .env if present (works even without python-dotenv)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT/".env", override=True)
except Exception:
    envp = ROOT/".env"
    if envp.exists():
        for ln in envp.read_text().splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k,v = ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

# read quick context
strategy = os.getenv("STRATEGY", "unknown")
cooldown = os.getenv("ALERT_COOLDOWN_SEC", "120")

# last push/log time (best-effort; ignore errors)
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception: return "n/a"

git_head = sh(f"cd {ROOT} && git rev-parse --short HEAD 2>/dev/null || echo n/a")
log_line = sh(f"tail -n 1 {ROOT}/data/autopilot.out 2>/dev/null || true")

# notify bridge
spec = importlib.util.spec_from_file_location("notify", str(ROOT/"scripts"/"notify.py"))
mod  = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
msg = (
    f"✅ Alive @ {now}\n"
    f"• strategy: {strategy}\n"
    f"• alert cooldown: {cooldown}s\n"
    f"• git: {git_head}\n"
    f"• last log: {log_line[:180]}"
)
ok = mod.send(msg)  # type: ignore
print({"sent": bool(ok)})
