#!/usr/bin/env python3
from __future__ import annotations
import os, importlib, json
from pathlib import Path as _P
try:
    from dotenv import load_dotenv as _ld
    _ld(_P.home()/ 'angel-one-smart-bot'/ '.env', override=True)
except Exception:
    pass
def _read_env_key(k, default=''):
    v = os.getenv(k)
    if v is not None: return v
    try:
        for ln in (_P.home()/ 'angel-one-smart-bot'/ '.env').read_text().splitlines():
            if ln.startswith(k+'='):
                return ln.split('=',1)[1].strip()
    except Exception: pass
    return default
STRATEGY = _read_env_key('STRATEGY','pcr_momentum_oi')
strat = importlib.import_module(f'strategies.{STRATEGY}')
try:
    print(json.dumps({'event':'strategy_selected','name':STRATEGY}), flush=True)
except Exception:
    pass
# === /STRATEGY_WIRING ===
import os, sys, time, json, traceback
from pathlib import Path
# --- load .env (force override) ---
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path.home()/ "angel-one-smart-bot"/ ".env", override=True)
except Exception:
    pass
# --- telegram notify ---
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send
# --- Angel One SmartAPI login (MPIN + TOTP) ---
def smart_login():
    try:
        try:
            from SmartApi import SmartConnect      # your env has SmartApi
        except ModuleNotFoundError:
            from smartapi import SmartConnect      # fallback
        import pyotp
        cid   = os.getenv("CLIENT_CODE")
        akey  = os.getenv("API_KEY")
        asec  = os.getenv("API_SECRET")            # reserved if needed later
        mpin  = os.getenv("MPIN")
        tsec  = os.getenv("TOTP_SECRET")
        if not all([cid, akey, mpin, tsec]):
            raise RuntimeError("Missing SmartAPI creds in .env")
        otp = pyotp.TOTP(tsec).now()
        obj = SmartConnect(api_key=akey)
        resp = obj.generateSession(cid, mpin, otp)
        if not resp or str(resp.get("status")).lower() not in ("ok","true","success"):
            raise RuntimeError(f"Login failed: {resp}")
        return obj, cid
    except Exception as e:
        raise
# --- strategy tick shim ---
def call_strategy_tick(api=None, live=False):
    try:
        import os, importlib
        name = os.getenv('STRATEGY','pcr_momentum_oi')
        strat = importlib.import_module(f'strategies.{name}')
    except Exception:
        return
    for fn_name in ("tick","run","main"):
        fn = getattr(strat, fn_name, None)
        if callable(fn):
            try:
                try:
                    fn(api, live=live)
                except TypeError:
                    try:
                        fn(live=live)
                    except TypeError:
                        try:
                            fn(api)
                        except TypeError:
                            fn()
            except Exception:
                raise
            return
def within_market_ist():
    from datetime import datetime, time as dtime
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        now = datetime.utcnow()
    if now.isoweekday() > 5:  # Sat/Sun
        return False
    start = dtime(9,15)
    end   = dtime(15,25)
    return start <= now.time() <= end
def main():
    # === ENV BOOTSTRAP ===
    try:
        if 'load_dotenv' in globals() and load_dotenv is not None:
            root = Path.home()/ 'angel-one-smart-bot'
            load_dotenv(root/'.env', override=True)
    except Exception:
        pass
    ROOT = Path.home()/ "angel-one-smart-bot"
    (ROOT/"data").mkdir(parents=True, exist_ok=True)
    LIVE = os.getenv("LIVE","0")=="1"
    DRY  = os.getenv("DRY","1")=="1"
    mode = "LIVE" if LIVE and not DRY else "DRY"
    # log chosen strategy once at startup
    _strat = os.getenv('STRATEGY','pcr_momentum_oi')
    try:
        send(f"Autopilot started ✅ (mode: {mode}) — strategy: {_strat}")
    except Exception:
        pass
    try:
        send(f"Autopilot started ✅ (mode: {mode})")
    except:
        pass
    api=None; cid=None; last_login=0; backoff=5
    while True:
        try:
            now=time.time()
            # relogin every ~45 min or if missing
            if api is None or (now-last_login)>45*60:
                api=None
                try:
                    api,cid=smart_login()
                    last_login=time.time(); backoff=5
                    print(json.dumps({"event":"login_ok"}), flush=True)
                    try: send("SmartAPI login OK ✅")
                    except: pass
                except Exception as e:
                    print(json.dumps({"event":"login_fail","err":str(e)}), flush=True)
                    try: send(f"SmartAPI login FAIL ❌: {e}")
                    except: pass
                    time.sleep(min(backoff,120)); backoff=min(backoff*2,120)
                    continue
            if within_market_ist():
                try:
                    call_strategy_tick(api=api, live=(LIVE and not DRY))
                except Exception as e:
                    tb=traceback.format_exc()[-2000:]
                    print(json.dumps({"event":"strategy_error","err":str(e)}), flush=True)
                    try: send(f"Strategy error ❌ {type(e).__name__}: {e}\n{tb}")
                    except: pass
                    time.sleep(2)
            else:
                time.sleep(10)
            time.sleep(1.0)
        except KeyboardInterrupt:
            print(json.dumps({"event":"shutdown"}), flush=True); break
        except Exception as e:
            tb=traceback.format_exc()[-2000:]
            try: send(f"Autopilot crash/restart: {type(e).__name__}: {e}\n{tb}")
            except: pass
            print(json.dumps({"event":"crash","err":str(e)}), flush=True)
            time.sleep(3)
if __name__=="__main__":
    sys.exit(main())
# === STRATEGY_WIRING (do not move) ===
