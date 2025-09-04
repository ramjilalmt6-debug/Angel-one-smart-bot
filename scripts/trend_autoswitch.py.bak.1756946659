#!/usr/bin/env python3
from __future__ import annotations
import os, json, subprocess, sys
from pathlib import Path
from datetime import datetime

ROOT = Path.home()/ "angel-one-smart-bot"
ENV  = ROOT/ ".env"
DATA = ROOT/ "data"
VOTE = DATA/ "trend_vote.json"
DATA.mkdir(parents=True, exist_ok=True)

# --- env ---
try:
    from dotenv import load_dotenv
    load_dotenv(ENV, override=True)
except Exception:
    pass

# --- notifier shim ---
try:
    from scripts.notify import send as _send
except Exception:
    try:
        from notify import send as _send
    except Exception:
        def _send(*a, **k): return False
send = _send

def read_env_key(k: str, default: str = "") -> str:
    # Prefer in-memory env (dotenv loaded), but also read file if missing
    v = os.getenv(k)
    if v is not None:
        return v
    try:
        for ln in ENV.read_text().splitlines():
            if ln.startswith(f"{k}="):
                return ln.split("=",1)[1].strip()
    except Exception:
        pass
    return default

def set_env_key(k: str, v: str) -> None:
    ENV.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    found = False
    if ENV.exists():
        for ln in ENV.read_text().splitlines():
            if ln.startswith(f"{k}="):
                lines.append(f"{k}={v}")
                found = True
            else:
                lines.append(ln)
    if not found:
        lines.append(f"{k}={v}")
    ENV.write_text("\n".join([l for l in lines if l.strip() != ""]) + "\n")
    try:
        os.chmod(ENV, 0o600)
    except Exception:
        pass

def call_check() -> dict:
    res = subprocess.run(
        ["bash","-lc", f"{ROOT}/scripts/trend_check.py"],
        capture_output=True, text=True
    )
    out = (res.stdout or "").strip()
    if not out:
        raise RuntimeError("trend_check produced no output")
    # trend_check prints exactly one JSON line
    try:
        return json.loads(out.splitlines()[-1])
    except Exception:
        raise RuntimeError(f"bad JSON: {out!r}")

def read_vote() -> dict:
    try:
        return json.loads(VOTE.read_text())
    except Exception:
        return {"want": None, "vote": 0, "ts": 0}

def write_vote(d: dict) -> None:
    d = dict(d)
    d["ts"] = int(datetime.now().timestamp())
    VOTE.write_text(json.dumps(d))

def main() -> int:
    if os.getenv("TREND_SWITCH_ENABLE","1") not in ("1","true","TRUE","yes","YES"):
        print(json.dumps({"event":"trend_switch_skipped","reason":"disabled"}))
        return 0

    min_c = int(os.getenv("TREND_MIN_CANDLES","20"))      # switch only if enough candles
    votes_needed = int(os.getenv("TREND_VOTES","2"))      # need N consecutive same suggestions

    cur = read_env_key("STRATEGY","pcr_momentum_oi")

    try:
        J = call_check()
    except Exception as e:
        send(f"⚠️ TrendCheck failed: {type(e).__name__}: {e}")
        print(json.dumps({"event":"trend_switch_error","err":str(e)}))
        return 1

    want = str(J.get("strategy") or cur)
    adx  = float(J.get("adx") or 0.0)
    used = int(J.get("candles_used") or 0)
    status = str(J.get("status") or "-")
    meta = J.get("meta", {})

    if used < min_c:
        print(json.dumps({"event":"trend_switch_hold","reason":"not_enough_candles","candles":used,"need":min_c}))
        return 0

    if want == cur:
        # reset vote when aligned
        write_vote({"want": want, "vote": 0})
        print(json.dumps({"event":"trend_switch_nop","strategy":cur,"adx":adx,"status":status}))
        return 0

    v = read_vote()
    if v.get("want") == want:
        v["vote"] = int(v.get("vote",0)) + 1
    else:
        v = {"want": want, "vote": 1}
    write_vote(v)

    if v["vote"] >= votes_needed:
        # switch
        set_env_key("STRATEGY", want)
        # restart runner
        subprocess.run(["bash","-lc", f"{ROOT}/scripts/guardian.sh"], check=False)
        send(f"🔀 Strategy switched → {want}  (ADX {adx:.1f}, {status})")
        print(json.dumps({"event":"trend_switched","from":cur,"to":want,"adx":adx,"status":status,"meta":meta}))
        # reset vote after switch
        write_vote({"want": None, "vote": 0})
    else:
        print(json.dumps({"event":"trend_vote","want":want,"vote":v['vote'],"need":votes_needed,"adx":adx,"status":status}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
