#!/usr/bin/env python3
from __future__ import annotations
import os, json, time, subprocess
from pathlib import Path
from datetime import datetime, time as _t

ROOT = Path.home() / "angel-one-smart-bot"
LOG  = ROOT / "data" / "autopilot.out"

# --- load .env ---
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env", override=True)
except Exception:
    pass

# --- notify shim ---
def _send_stub(*a, **k): return False
try:
    from scripts.notify import send as send
except Exception:
    try:
        from notify import send as send
    except Exception:
        send = _send_stub

def is_market_hours_ist(now: datetime) -> bool:
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end   = now.replace(hour=16, minute=0, second=59, microsecond=0)
    # Monday(0) .. Friday(4)
    return now.weekday() <= 4 and start <= now <= end

def log_fresh_enough(max_age_min: int) -> tuple[bool, float]:
    try:
        mtime = LOG.stat().st_mtime
        age_s = time.time() - mtime
        return (age_s <= max_age_min*60, age_s/60.0)
    except FileNotFoundError:
        return (False, float("inf"))

def autopilot_running() -> bool:
    try:
        out = subprocess.check_output(
            ["bash","-lc","pgrep -af 'scripts/autopilot.py'"], text=True
        ).strip()
        return bool(out)
    except subprocess.CalledProcessError:
        return False

def main() -> int:
    now = datetime.now()
    market  = is_market_hours_ist(now)
    max_age = 6 if market else 60

    issues = []

    ok, age_min = log_fresh_enough(max_age)
    if not ok:
        issues.append(f"⚠️ Log stale: {int(age_min)} min (limit {max_age} min)")

    if not autopilot_running():
        issues.append("❌ autopilot.py not running")

    payload = {
        "event": "health_sentinel_report",
        "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        "market_hours": market,
        "max_age_min": max_age,
        "issues": issues or ["✅ OK"],
    }

    # Notify only when there are real issues (not the “OK” placeholder)
    if issues:
        send(" / ".join(issues))

    print(json.dumps(payload, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
