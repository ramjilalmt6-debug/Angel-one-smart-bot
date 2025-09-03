from __future__ import annotations
import os, pathlib, datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
TZ   = ZoneInfo(os.getenv("TIMEZONE","Asia/Kolkata"))

def is_market_open(now=None):
    now = now or datetime.datetime.now(TZ)
    # Mon-Fri 09:15–15:30 IST (basic check; add holidays as needed)
    if now.weekday() >= 5: return False
    t = now.time()
    return (t >= datetime.time(9,15)) and (t <= datetime.time(15,30))

def mode():
    m = os.getenv("MODE","DRY").upper()
    if m != "LIVE": return "DRY"
    if not (ROOT/"flags"/"live.ok").exists(): return "DRY"
    return "LIVE"

def live_ready():
    return mode()=="LIVE" and is_market_open()
