#!/usr/bin/env python3
from __future__ import annotations
import os, json, time, traceback
from pathlib import Path

# env
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path.home()/ "angel-one-smart-bot"/ ".env", override=True)
except Exception:
    pass

# notify
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send


ROOT = Path.home()/ "angel-one-smart-bot"
ENVF = ROOT/".env"

def read_env_num(key, default=0.0):
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default

DAILY_SL = read_env_num("DAILY_SL", 0.0)
DAILY_TP = read_env_num("DAILY_TP", 0.0)

def mode() -> str:
    live = os.getenv("LIVE","0")=="1"
    dry  = os.getenv("DRY","1")=="1"
    return "LIVE" if live and not dry else "DRY"

def get_pnl() -> float | None:
    # test override: explicit PnL
    try:
        fp = os.getenv("FORCE_PNL")
        if fp not in (None, "", "None"):
            return float(fp)
    except Exception:
        pass

    # testing mode: prefer file, skip SmartAPI
    if os.getenv("RISK_SOURCE","").lower() == "file":
        try:
            j = json.loads((ROOT/"data"/"pnl.json").read_text())
            return float(j.get("pnl"))
        except Exception:
            return None

    # 1) try SmartAPI positions
    SmartConnect = None
    try:
        from SmartApi import SmartConnect as _S
        SmartConnect = _S
    except ModuleNotFoundError:
        try:
            from smartapi import SmartConnect as _S
            SmartConnect = _S
        except Exception:
            SmartConnect = None

    if SmartConnect:
        try:
            import pyotp
            cid=os.getenv("CLIENT_CODE"); akey=os.getenv("API_KEY")
            mpin=os.getenv("MPIN"); tsec=os.getenv("TOTP_SECRET")
            if all([cid, akey, mpin, tsec]):
                otp = pyotp.TOTP(tsec).now()
                api = SmartConnect(api_key=akey)
                api.generateSession(cid, mpin, otp)
                # positions endpoint name varies; try common ones:
                for fn in ("position", "positions", "getPosition", "getPositions"):
                    f = getattr(api, fn, None)
                    if callable(f):
                        resp = f()
                        data = resp.get("data") if isinstance(resp, dict) else resp
                        total = 0.0; found=False
                        if isinstance(data, (list, tuple)):
                            for p in data:
                                if not isinstance(p, dict): continue
                                for k in ("pnl","unrealized","unrealised","unrealizedPnL","netPnL","netpnl","NetPnL"):
                                    if k in p:
                                        try:
                                            total += float(p[k]); found=True
                                            break
                                        except Exception:
                                            pass
                        if found:
                            return float(total)
        except Exception:
            pass

    # 2) optional: data/pnl.json written by strategy
    try:
        j = json.loads((ROOT/"data"/"pnl.json").read_text())
        return float(j.get("pnl"))
    except Exception:
        return None

def flip_to_dry():
    # safest: LIVE=0, DRY=1
    import tempfile
    tmp = Path(tempfile.mkstemp()[1])
    lines = []
    if ENVF.exists():
        lines = ENVF.read_text().splitlines()
    def upsert(k,v):
        nonlocal lines
        for i,l in enumerate(lines):
            if l.startswith(k+"="):
                lines[i]=f"{k}={v}"; break
        else:
            lines.append(f"{k}={v}")
    upsert("LIVE","0"); upsert("DRY","1")
    tmp.write_text("\n".join(lines)+"\n")
    tmp.replace(ENVF)
    os.chmod(ENVF, 0o600)

def main():
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cur_mode = mode()
    if cur_mode != "LIVE":
        print(json.dumps({"event":"risk_guard_skip","mode":cur_mode,"ts":now}), flush=True)
        return 0

    pnl = get_pnl()
    if pnl is None:
        send("⚠️ Risk-Guard: PnL fetch failed (no action). Consider wiring data/pnl.json or SmartAPI positions.")
        print(json.dumps({"event":"risk_guard_pnl_none"}), flush=True)
        return 0

    breach = None
    if DAILY_SL and pnl <= -abs(DAILY_SL):
        breach = f"Daily SL hit: {pnl:.2f} ≤ -{abs(DAILY_SL):.2f}"
    if DAILY_TP and pnl >= abs(DAILY_TP):
        breach = breach or f"Daily TP hit: {pnl:.2f} ≥ {abs(DAILY_TP):.2f}"

    if not breach:
        print(json.dumps({"event":"risk_guard_ok","pnl":pnl}), flush=True)
        return 0

    # action: flip to DRY, call optional square-off hook, notify
    flip_to_dry()
    try:
        # optional square-off hook (no-op if missing)
        so = ROOT/"scripts"/"square_off_all.sh"
        if so.exists():
            os.system(f"bash -lc '{so}'")
    except Exception:
        pass

    msg = f"🛑 Risk-Guard: {breach}\nAction: LIVE→0, DRY→1 (trading paused for safety)."
    send(msg)
    print(json.dumps({"event":"risk_guard_flip","reason":breach,"pnl":pnl,"ts":now}), flush=True)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit as e:
        raise
    except Exception as e:
        try:
            send(f"Risk-Guard crashed: {type(e).__name__}: {e}\n{traceback.format_exc()[-1000:]}")
        except Exception:
            pass
        print(json.dumps({"event":"risk_guard_crash","err":str(e)}), flush=True)
        raise
