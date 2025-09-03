#!/usr/bin/env python3
from __future__ import annotations
import os, json
from pathlib import Path

ROOT = Path.home() / "angel-one-smart-bot"

# --- env ---
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

# --- notifier (robust shim) ---
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

def is_live_mode() -> bool:
    return os.getenv("LIVE","0") == "1" and os.getenv("DRY","1") != "1"

def main() -> int:
    # Safety: only act in LIVE
    if not is_live_mode():
        print(json.dumps({"event":"square_off_skip","reason":"not_live"}), flush=True)
        send("ℹ️ Square-Off skipped: bot is not in LIVE mode.")
        return 0

    # SmartAPI creds
    try:
        import pyotp
    except Exception:
        print(json.dumps({"event":"square_off_skip","reason":"pyotp_missing"}), flush=True)
        send("⚠️ Square-Off skipped: pyotp not available.")
        return 0

    cid  = os.getenv("CLIENT_CODE")
    akey = os.getenv("API_KEY")
    mpin = os.getenv("MPIN")
    tsec = os.getenv("TOTP_SECRET")
    if not all([cid, akey, mpin, tsec]):
        print(json.dumps({"event":"square_off_skip","reason":"missing_creds"}), flush=True)
        send("⚠️ Square-Off skipped: SmartAPI creds missing.")
        return 0

    # Login
    try:
        SC  = smart_connect()
        otp = pyotp.TOTP(tsec).now()
        api = SC(api_key=akey)
        api.generateSession(cid, mpin, otp)
    except Exception as e:
        send(f"❌ Square-Off login failed: {type(e).__name__}: {e}")
        print(json.dumps({"event":"square_off_fail","stage":"login","err":str(e)}), flush=True)
        return 1

    # Pull positions
    positions = None
    try:
        for fn in ("getPositions","getPosition","positions","position"):
            f = getattr(api, fn, None)
            if callable(f):
                resp = f()
                positions = resp.get("data") if isinstance(resp, dict) else resp
                break
    except Exception:
        positions = None

    if not isinstance(positions, (list, tuple)):
        send("⚠️ Square-Off: positions fetch failed.")
        print(json.dumps({"event":"square_off_fail","reason":"no_positions"}), flush=True)
        return 1

    # Attempt exit for any open qty
    exits = 0
    for p in positions:
        if not isinstance(p, dict):
            continue

        # net quantity detection
        qty = None
        for qk in ("netqty","netQty","net_quantity","netQuantity"):
            if qk in p:
                try:
                    qty = int(float(p[qk]))
                    break
                except Exception:
                    pass
        if not qty:
            continue

        tradingsymbol = p.get("tradingsymbol") or p.get("tsym") or p.get("symbol")
        exch = p.get("exchange") or p.get("exch") or "NFO"

        try:
            # Try built-ins first
            for fn in ("squareOff","exitPosition","exitByProduct"):
                f = getattr(api, fn, None)
                if callable(f):
                    try:
                        # call with no args or with exch/tsym if accepted
                        if getattr(f, "__code__", None) and f.__code__.co_argcount == 1:
                            f_resp = f()
                        else:
                            args = {"exch": exch, "tradingsymbol": tradingsymbol}
                            f_resp = f(**{k:v for k,v in args.items() if v})
                        exits += 1
                        break
                    except Exception:
                        pass
            else:
                # Fallback: opposite market order
                side = "SELL" if qty > 0 else "BUY"
                place = getattr(api, "placeOrder", None)
                if callable(place) and tradingsymbol:
                    try:
                        placevar = {
                            "variety": "NORMAL",
                            "tradingsymbol": tradingsymbol,
                            "symboltoken": p.get("symboltoken") or p.get("token"),
                            "transactiontype": side,
                            "exchange": exch,
                            "ordertype": "MARKET",
                            "producttype": p.get("producttype") or p.get("product") or "INTRADAY",
                            "duration": "DAY",
                            "price": "0",
                            "squareoff": "0",
                            "stoploss": "0",
                            "quantity": str(abs(int(qty))),
                        }
                        place(**{k:v for k,v in placevar.items() if v is not None})
                        exits += 1
                    except Exception:
                        pass
        except Exception:
            pass

    send(f"🧹 Square-Off executed: attempted exits={exits}.")
    print(json.dumps({"event":"square_off_done","attempted":exits}), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
