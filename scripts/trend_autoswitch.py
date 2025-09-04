#!/usr/bin/env python3
from __future__ import annotations
import os, json, subprocess
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path.home()/ "angel-one-smart-bot"
ENV  = ROOT/ ".env"
DATA = ROOT/ "data"
VOTE = DATA/ "trend_vote.json"
SWITCHLOG = DATA/ "switches.jsonl"
DATA.mkdir(parents=True, exist_ok=True)

# --- env ---
try:
    from dotenv import load_dotenv
    load_dotenv(ENV, override=True)
except Exception:
    # minimal fallback: read file and setenv
    try:
        for ln in ENV.read_text().splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

# --- notifier shim ---
def _noop(*a, **k): return False
send = _noop
for modname in ("scripts.notify", "notify", "core.notify"):
    try:
        mod = __import__(modname, fromlist=["send"])
        send = getattr(mod, "send", _noop)
        break
    except Exception:
        pass

def read_env_key(k: str, default: str = "") -> str:
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
    lines, found = [], False
    if ENV.exists():
        for ln in ENV.read_text().splitlines():
            if ln.startswith(f"{k}="):
                lines.append(f"{k}={v}")
                found = True
            elif ln.strip():
                lines.append(ln)
    if not found:
        lines.append(f"{k}={v}")
    ENV.write_text("\n".join(lines) + "\n")
    try: os.chmod(ENV, 0o600)
    except Exception: pass

def call_check() -> dict:
    res = subprocess.run(
        ["bash","-lc", f"{ROOT}/scripts/trend_check.py"],
        capture_output=True, text=True
    )
    out = (res.stdout or "").strip()
    if not out:
        raise RuntimeError("trend_check produced no output")
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
    d = dict(d); d["ts"] = int(datetime.now().timestamp())
    VOTE.write_text(json.dumps(d))

# --- switch safety rails ---
def _now():
    return datetime.now()

def _log_switch(entry: dict) -> None:
    SWITCHLOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SWITCHLOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _last_switch_ts() -> int | None:
    if not SWITCHLOG.exists():
        return None
    try:
        *_, last = SWITCHLOG.read_text().splitlines()
        j = json.loads(last)
        return int(j.get("ts", 0)) or None
    except Exception:
        return None

def _count_switches_today() -> int:
    if not SWITCHLOG.exists():
        return 0
    today = _now().date().isoformat()
    cnt = 0
    try:
        with open(SWITCHLOG) as f:
            for ln in f:
                try:
                    j = json.loads(ln)
                    ts = j.get("ts")
                    if not ts: continue
                    if datetime.fromtimestamp(int(ts)).date().isoformat() == today:
                        cnt += 1
                except Exception:
                    pass
    except Exception:
        pass
    return cnt

def main() -> int:
    if os.getenv("TREND_SWITCH_ENABLE","1") not in ("1","true","TRUE","yes","YES"):
        print(json.dumps({"event":"trend_switch_skipped","reason":"disabled"}))
        return 0

    # knobs
    min_c = int(os.getenv("TREND_MIN_CANDLES","20"))
    votes_needed = int(os.getenv("TREND_VOTES","2"))
    cooldown_min = int(os.getenv("TREND_SWITCH_COOLDOWN_MIN","15"))
    max_per_day  = int(os.getenv("TREND_SWITCH_MAX_PER_DAY","3"))

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
        write_vote({"want": want, "vote": 0})
        print(json.dumps({"event":"trend_switch_nop","strategy":cur,"adx":adx,"status":status}))
        return 0

    # vote gate
    v = read_vote()
    v = {"want": want, "vote": int(v.get("vote",0)) + 1} if v.get("want") == want else {"want": want, "vote": 1}
    write_vote(v)
    if v["vote"] < votes_needed:
        print(json.dumps({"event":"trend_vote","want":want,"vote":v['vote'],"need":votes_needed,"adx":adx,"status":status}))
        return 0

    # safety rails
    now = _now()
    last_ts = _last_switch_ts()
    if last_ts:
        since = now - datetime.fromtimestamp(last_ts)
        if since < timedelta(minutes=cooldown_min):
            wait_left = int((timedelta(minutes=cooldown_min) - since).total_seconds() // 60) + 1
            print(json.dumps({"event":"trend_switch_cooldown","wait_min":wait_left,"cooldown_min":cooldown_min}))
            return 0

    today_count = _count_switches_today()
    if today_count >= max_per_day:
        print(json.dumps({"event":"trend_switch_cap","today":today_count,"max_per_day":max_per_day}))
        return 0

    # do switch
    prev = cur
    set_env_key("STRATEGY", want)
    subprocess.run(["bash","-lc", f"{ROOT}/scripts/guardian.sh"], check=False)

    entry = {
        "event":"trend_switched","from":prev,"to":want,"adx":adx,
        "status":status,"meta":meta,"ts":int(now.timestamp())
    }
    _log_switch(entry)
    send(f"🔀 Strategy switched → {want}  (ADX {adx:.1f}, {status})")
    print(json.dumps(entry))
    write_vote({"want": None, "vote": 0})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
