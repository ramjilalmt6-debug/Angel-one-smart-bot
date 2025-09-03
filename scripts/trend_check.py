#!/usr/bin/env python3
from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime, timedelta, time as _t

# --- load .env ---
try:
    from dotenv import load_dotenv
    load_dotenv(Path.home()/ "angel-one-smart-bot"/ ".env", override=True)
except Exception:
    pass

def smart_connect():
    try:
        from SmartApi import SmartConnect
    except ModuleNotFoundError:
        from smartapi import SmartConnect
    return SmartConnect

def ist_now() -> datetime:
    # Termux is already IST per your setup; if not, adjust here.
    return datetime.now()

def market_window_ist(now: datetime, minutes_back: int):
    """
    Clamp from/to to the latest valid market window:
    09:15 to 15:30 IST for cash/indices.
    """
    d = now.date()
    start_day = datetime.combine(d, _t(9, 15))
    end_day   = datetime.combine(d, _t(15, 30))
    if now < start_day:
        # before open -> use previous session (simple: previous calendar day)
        prev = now - timedelta(days=1)
        d = prev.date()
        start_day = datetime.combine(d, _t(9, 15))
        end_day   = datetime.combine(d, _t(15, 30))
    elif now > end_day:
        # after close -> cap to 15:30
        pass
    # default: within session; cap end to min(now, 15:30)
    end_ts = min(now, end_day)
    start_ts = max(start_day, end_ts - timedelta(minutes=minutes_back))
    # SmartAPI expects "YYYY-mm-dd HH:MM"
    return start_ts.strftime("%Y-%m-%d %H:%M"), end_ts.strftime("%Y-%m-%d %H:%M")

def fetch_candles():
    # env
    exch_env   = os.getenv("TREND_EXCHANGE", "NSE")
    token      = os.getenv("TREND_SYMBOLTOKEN", "")
    interval   = os.getenv("TREND_INTERVAL", "FIVE_MINUTE")
    look_min   = int(os.getenv("TREND_LOOKBACK_MIN", "180"))

    if not token:
        raise SystemExit("TREND_SYMBOLTOKEN missing in .env")

    cid  = os.getenv("CLIENT_CODE")
    akey = os.getenv("API_KEY")
    mpin = os.getenv("MPIN")
    tsec = os.getenv("TOTP_SECRET")
    if not all([cid, akey, mpin, tsec]):
        raise SystemExit("SmartAPI creds missing in .env")

    # login
    SC = smart_connect()
    import pyotp
    otp = pyotp.TOTP(tsec).now()
    api = SC(api_key=akey)
    api.generateSession(cid, mpin, otp)

    # window
    start_s, end_s = market_window_ist(ist_now(), look_min)

    # try multiple exchanges (helps for indices)
    exchanges = [exch_env, "NSE", "NSE_INDICES", "INDICES", "CDS"]
    seen = []
    for ex in exchanges:
        if not ex or ex in seen: 
            continue
        seen.append(ex)
        try:
            resp = api.getCandleData({
                "exchange": ex,
                "symboltoken": token,
                "interval": interval,
                "fromdate": start_s,
                "todate":   end_s,
            })
            data = resp.get("data") if isinstance(resp, dict) else resp
            if data:
                return data, {"exchange": ex, "from": start_s, "to": end_s, "interval": interval}
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"

    # no data
    meta = {"exchange_tried": seen, "from": start_s, "to": end_s, "interval": interval}
    raise SystemExit(json.dumps({"error":"no_candles","meta":meta,"hint":"Check token/exchange"}, ensure_ascii=False))

def compute_adx(candles, period: int = 14) -> float:
    """
    candles rows from SmartAPI are usually:
    [time, open, high, low, close, volume]
    """
    if len(candles) < period + 1:
        return 0.0

    highs  = [float(c[2]) for c in candles]
    lows   = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]

    tr_list, pdm_list, ndm_list = [], [], []
    for i in range(1, len(highs)):
        high, low, prev_close = highs[i], lows[i], closes[i-1]
        tr  = max(high - low, abs(high - prev_close), abs(low - prev_close))
        up  = highs[i] - highs[i-1]
        dn  = lows[i-1] - lows[i]
        pdm = up if (up > dn and up > 0) else 0.0
        ndm = dn if (dn > up and dn > 0) else 0.0
        tr_list.append(tr); pdm_list.append(pdm); ndm_list.append(ndm)

    # simple averages (good enough for switch signal)
    if len(tr_list) < period:
        return 0.0
    atr = sum(tr_list[:period]) / period
    if atr == 0:
        return 0.0
    pdi = 100.0 * (sum(pdm_list[:period]) / atr)
    ndi = 100.0 * (sum(ndm_list[:period]) / atr)
    denom = (pdi + ndi)
    dx = 100.0 * abs(pdi - ndi) / denom if denom != 0 else 0.0
    return float(dx)

def main():
    try:
        candles, meta = fetch_candles()
    except SystemExit as e:
        # pass through structured json if provided
        msg = str(e)
        if msg.startswith("{"):
            print(msg)
        else:
            print(json.dumps({"error":"fetch_failed","detail":msg}, ensure_ascii=False))
        return

    adx = compute_adx(candles)
    th_trend = float(os.getenv("TREND_ADX_TREND", "20"))
    th_range = float(os.getenv("TREND_ADX_RANGE", "18"))

    if adx >= th_trend:
        status, new_strat = "Trending", "breakout_atr"
    elif adx <= th_range:
        status, new_strat = "Range", "pcr_momentum_oi"
    else:
        status, new_strat = "Neutral", os.getenv("STRATEGY", "pcr_momentum_oi")

    print(json.dumps({
        "adx": round(adx, 2),
        "status": status,
        "strategy": new_strat,
        "candles_used": len(candles),
        "meta": meta
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
