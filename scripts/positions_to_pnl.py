#!/usr/bin/env python3
from __future__ import annotations
import os, json, time
from pathlib import Path

ROOT = Path.home() / "angel-one-smart-bot"
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "pnl.json"

# --- env ---
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / ".env", override=True)
except Exception:
    pass

# --- notify (best-effort) ---
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send


def smart_connect():
    try:
        from SmartApi import SmartConnect
    except ModuleNotFoundError:
        from smartapi import SmartConnect
    return SmartConnect

def fetch_positions_pnl() -> float | None:
    SC = smart_connect()
    try:
        import pyotp
        cid  = os.getenv("CLIENT_CODE")
        akey = os.getenv("API_KEY")
        mpin = os.getenv("MPIN")
        tsec = os.getenv("TOTP_SECRET")
        if not all([cid, akey, mpin, tsec]):
            return None

        otp = pyotp.TOTP(tsec).now()
        api = SC(api_key=akey)
        api.generateSession(cid, mpin, otp)

        # Try common method names for positions
        for fn in ("getPositions", "getPosition", "positions", "position"):
            f = getattr(api, fn, None)
            if not callable(f):
                continue
            resp = f()
            data = resp.get("data") if isinstance(resp, dict) else resp
            total = 0.0
            found = False
            if isinstance(data, (list, tuple)):
                for p in data:
                    if not isinstance(p, dict):
                        continue
                    for k in ("pnl","netpnl","NetPnL","unrealized","unrealised","unrealizedPnL"):
                        if k in p:
                            try:
                                total += float(p[k])
                                found = True
                                break
                            except Exception:
                                pass
            if found:
                return float(total)
    except Exception:
        return None
    return None

def main():
    pnl = fetch_positions_pnl()
    if pnl is None:
        # Keep last value; just heartbeat
        (DATA / "pnl_heartbeat.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        print(json.dumps({"event":"pnl_write_skip","reason":"none"}), flush=True)
        return 0

    OUT.write_text(json.dumps({"pnl": pnl, "ts": int(time.time())}) + "\n")
    print(json.dumps({"event":"pnl_written","pnl":pnl}), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
