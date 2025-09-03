#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import json
import random
import signal
import argparse
from datetime import datetime, time as dtime, timedelta, timezone

import pyotp
from SmartApi.smartConnect import SmartConnect
from SmartApi.smartExceptions import DataException

ap = argparse.ArgumentParser(description="Target + BE + Trailing SL watcher (Angel One SmartAPI).")
ap.add_argument("--ex", default="NFO")
ap.add_argument("--ts", required=True)
ap.add_argument("--tok", required=True)
ap.add_argument("--qty", type=int, required=True)
ap.add_argument("--target", type=float, required=True)
ap.add_argument("--trail-above", type=float, required=True)
ap.add_argument("--trail-gap", type=float, default=15.0)
ap.add_argument("--breakeven", type=float, required=True)
ap.add_argument("--entry", type=float, required=True)
ap.add_argument("--poll", type=float, default=0.8, help="LTP poll seconds")
ap.add_argument("--eod", default="15:18", help="EOD cutoff IST, e.g. 15:18")
args = ap.parse_args()

# --- IST timezone (Angel One market hours) ---
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

# --- Rate-limit tolerant helpers (Angel One API) ---
RL = (
    "Access denied because of exceeding access rate",
    "Too many requests",
    "Request rate limit exceeded",
)
def _rl(msg: str) -> bool:
    m = (msg or "").lower()
    return any(e.lower() in m for e in RL) or "couldn't parse the json" in m

def backoff(fn, tries=6, base=0.6, cap=5.0):
    last = None
    for i in range(tries):
        try:
            return fn()
        except DataException as e:
            last = e
            if not _rl(str(e)):
                raise
        except Exception as e:
            last = e
        time.sleep(min(cap, base*(2**i)) + random.uniform(0, 0.35))
    raise last or RuntimeError("retry exhausted")

# --- SmartAPI login (Angel One guideline) ---
API = os.environ.get("SMARTAPI_API_KEY")
CID = os.environ.get("SMARTAPI_CLIENT_CODE")
PWD = os.environ.get("SMARTAPI_PASSWORD")
TOTP = os.environ.get("TOTP_SECRET")
if not all([API, CID, PWD, TOTP]):
    print(json.dumps({"error":"Missing env SMARTAPI_API_KEY/SMARTAPI_CLIENT_CODE/SMARTAPI_PASSWORD/TOTP_SECRET"}))
    sys.exit(2)

sc = SmartConnect(API)
otp = pyotp.TOTP(TOTP).now()
login = sc.generateSession(CID, PWD, otp)
if not login or not login.get("status"):
    print(json.dumps({"error":"SmartAPI login failed","resp":login}, ensure_ascii=False))
    sys.exit(2)

# --- Args → locals ---
EX, TS, TOK, QTY = args.ex, args.ts, args.tok, int(args.qty)
TARGET        = float(args.target)
TRAIL_ABOVE   = float(args.trail_above)
TRAIL_GAP     = float(args.trail_gap)
BREAK_EVEN_AT = float(args.breakeven)
ENTRY_PRICE   = float(args.entry)
POLL_S        = float(args.poll)
hh, mm = map(int, args.eod.split(":"))
EOD_CUTOFF = dtime(hh, mm)

# --- Thin wrappers (Angel One-compliant fields) ---
def order_book():
    return backoff(lambda: sc.orderBook()).get("data", [])

def cancel_sl(oid: str):
    return backoff(lambda: sc.cancelOrder("STOPLOSS", oid))

def modify_sl(oid: str, price: float, trigger: float):
    params = {
        "variety": "STOPLOSS",
        "orderid": oid,
        "ordertype": "STOPLOSS_LIMIT",  # SL-L
        "price": round(price, 2),
        "triggerprice": round(trigger, 2),
        "quantity": QTY,
        "exchange": EX,
        "tradingsymbol": TS,
        "symboltoken": TOK,
        "producttype": "INTRADAY",
        "duration": "DAY",
        "transactiontype": "SELL",
    }
    return backoff(lambda: sc.modifyOrder("STOPLOSS", oid, params))

def place_sl(price: float, trigger: float):
    order = {
        "variety":"STOPLOSS",
        "tradingsymbol": TS,
        "symboltoken": TOK,
        "transactiontype":"SELL",
        "exchange": EX,
        "ordertype":"STOPLOSS_LIMIT",  # SL-L
        "producttype":"INTRADAY",
        "duration":"DAY",
        "quantity": QTY,
        "price": round(price, 2),
        "triggerprice": round(trigger, 2),
    }
    return backoff(lambda: sc.placeOrder(order))

def sell_mkt():
    order = {
        "variety":"NORMAL",
        "tradingsymbol":TS,
        "symboltoken":TOK,
        "transactiontype":"SELL",
        "exchange":EX,
        "ordertype":"MARKET",
        "producttype":"INTRADAY",
        "duration":"DAY",
        "quantity":QTY,
    }
    return backoff(lambda: sc.placeOrder(order))

def current_sl():
    for o in order_book():
        if o.get("tradingsymbol")==TS and o.get("exchange")==EX and o.get("variety")=="STOPLOSS" and o.get("transactiontype")=="SELL":
            return o
    return None

def ltp():
    try:
        q = sc.ltpData(EX, TS, TOK)
        if q and q.get("status"):
            return float(q["data"]["ltp"])
    except Exception:
        pass
    q = sc.quote(EX, TS, TOK)
    if q and q.get("status"):
        return float(q["data"]["ltp"])
    raise RuntimeError("ltp failed")

# --- Graceful stop ---
running = True
def _stop(*a):
    global running
    running = False
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

sl = current_sl()
if sl:
    print("SL found:", json.dumps({k: sl.get(k) for k in ("orderid","price","triggerprice","orderstatus")}))
else:
    print("No existing SL (optional).")

trailing_base = None
print(f"Watch start → target:{TARGET} trail>{TRAIL_ABOVE} gap:{TRAIL_GAP} BE@{BREAK_EVEN_AT}")

while running:
    try:
        now_ist = datetime.now(IST).time()
        px = ltp()
        print("LTP:", px)

        # EOD square-off
        if now_ist >= EOD_CUTOFF:
            print("EOD cutoff → cancel SL → SELL MKT")
            if sl:
                try:
                    cancel_sl(sl["orderid"])
                except Exception as e:
                    print("SL cancel warn:", e)
            print(json.dumps(sell_mkt(), ensure_ascii=False))
            break

        # Target exit
        if px >= TARGET:
            print("Target hit → cancel SL → SELL MKT")
            if sl:
                try:
                    cancel_sl(sl["orderid"])
                except Exception as e:
                    print("SL cancel warn:", e)
            print(json.dumps(sell_mkt(), ensure_ascii=False))
            break

        # Break-even move
        if px >= BREAK_EVEN_AT:
            be_trig = round(max(ENTRY_PRICE - 0.05, 0), 2)
            be_lim  = round(be_trig - 0.05, 2)
            if sl:
                try:
                    print("Move SL to BE:", be_lim, be_trig)
                    modify_sl(sl["orderid"], be_lim, be_trig)
                except Exception as e:
                    print("modify BE failed, recreate:", e)
                    try:
                        cancel_sl(sl["orderid"])
                    except Exception as e2:
                        print("cancel warn:", e2)
                    place_sl(be_lim, be_trig)
                sl = current_sl()
            else:
                print("Place new BE SL:", be_lim, be_trig)
                place_sl(be_lim, be_trig)
                sl = current_sl()

        # Trailing after threshold
        if px >= TRAIL_ABOVE:
            trailing_base = max(trailing_base or px, px)
            want_trig = round(max(trailing_base - TRAIL_GAP, 0), 2)
            want_lim  = round(want_trig - 0.05, 2)
            if sl:
                cur_trig = float(sl.get("triggerprice") or 0)
                if want_trig > cur_trig + 0.01:
                    try:
                        print("Trail SL →", want_lim, want_trig)
                        modify_sl(sl["orderid"], want_lim, want_trig)
                    except Exception as e:
                        print("trail modify failed, recreate:", e)
                        try:
                            cancel_sl(sl["orderid"])
                        except Exception as e2:
                            print("cancel warn:", e2)
                        place_sl(want_lim, want_trig)
                    sl = current_sl()
            else:
                print("Place new trailing SL:", want_lim, want_trig)
                place_sl(want_lim, want_trig)
                sl = current_sl()

    except Exception as e:
        print("loop warn:", e)

    time.sleep(POLL_S)

print("Watcher stopped.")
