from __future__ import annotations
import os, json, time, re, subprocess, sys
from dataclasses import dataclass
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

HOME = os.path.expanduser("~")
BASE = f"{HOME}/angel-one-smart-bot"
ENV_PATH = f"{BASE}/.env"
DATA_DIR = f"{BASE}/data"
CONFIRM_PATH = f"{DATA_DIR}/confirm_live.json"
IST = ZoneInfo("Asia/Kolkata")

def load_env(path: str) -> dict[str,str]:
    env = {}
    if not os.path.isfile(path): return env
    for line in open(path, "r", encoding="utf-8"):
        line=line.strip()
        if not line or line.startswith("#"): continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
        if m:
            k,v = m.groups()
            env[k]=v.strip('"').strip("'")
    return env

def write_env(env: dict[str,str]) -> None:
    tmp = f"{ENV_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for k,v in env.items():
            f.write(f"{k}={v}\n")
    os.replace(tmp, ENV_PATH)

def ext_ip() -> str:
    try:
        return subprocess.check_output(["curl","-s","https://ifconfig.me"], timeout=6).decode().strip()
    except Exception:
        return ""

def send_tg(bot, chat, msg):
    if not (bot and chat): return
    try:
        subprocess.run([
            "curl","-s","-X","POST",
            f"https://api.telegram.org/bot{bot}/sendMessage",
            "-d",f"chat_id={chat}","--data-urlencode",f"text={msg}"
        ], check=False)
    except Exception:
        pass

@dataclass
class GuardResult:
    ok: bool
    reason: str

def within_market(env):
    now = datetime.now(IST)
    try:
        days = {int(x) for x in re.findall(r'\d+', env.get("MARKET_DAYS","1,2,3,4,5"))}
    except Exception:
        days = {1,2,3,4,5}
    if now.weekday() not in days:
        return GuardResult(False, f"weekday={now.weekday()}")
    rng = env.get("MARKET_HOURS","09:00-15:30").split("-")
    try:
        t1,t2=[dtime.fromisoformat(x) for x in rng]
        if not (t1 <= now.time() <= t2):
            return GuardResult(False, "outside market hours")
    except Exception:
        return GuardResult(False, "invalid MARKET_HOURS")
    return GuardResult(True, "market ok")

def vpn_locked(env):
    want = env.get("NORDVPN_REQUIRED_IP","").strip()
    got = ext_ip()
    if not want:
        return GuardResult(True, "no lock")
    if got == want:
        return GuardResult(True, f"vpn ok {got}")
    return GuardResult(False, f"vpn mismatch want={want} got={got}")

def ttl_ok(env, conf):
    ttl = int(env.get("LIVE_TTL_MIN","10") or "10")
    ts = int(conf.get("ts",0))
    if not ts:
        return GuardResult(False, "no ts")
    age = time.time() - ts
    return GuardResult(age <= ttl*60, f"age={int(age)}s ttl={ttl}m")

def main():
    env = load_env(ENV_PATH)
    auto = env.get("AUTO_SWITCH","0") == "1"
    if not auto:
        print("[i] AUTO_SWITCH off")
        return 0

    # Post cut-off → force DRY
    cut = env.get("AUTO_SQUAREOFF_TIME","15:25")
    try:
        hh,mm = map(int, cut.split(":"))
        if datetime.now(IST).time() >= dtime(hh,mm):
            env["DRY_RUN"] = "1"; write_env(env)
            send_tg(env.get("BOT_TOKEN"), env.get("CHAT_ID"), "🔒 Forced DRY after cutoff")
            print("[✓] Forced DRY after cutoff")
            return 0
    except Exception:
        pass

    # Read confirmation
    conf = {}
    if os.path.isfile(CONFIRM_PATH):
        try:
            conf = json.load(open(CONFIRM_PATH, "r", encoding="utf-8"))
        except Exception:
            conf = {}

    g1 = vpn_locked(env)
    g2 = within_market(env)
    g3 = GuardResult(conf.get("risk_ok", False), "risk_ok") if conf else GuardResult(False, "no confirm")
    g4 = ttl_ok(env, conf) if conf else GuardResult(False, "no confirm ttl")

    want_live = all([g1.ok, g2.ok, g3.ok, g4.ok])
    cur_live = (env.get("DRY_RUN","1") != "1")

    if want_live and not cur_live:
        env["DRY_RUN"] = "0"; write_env(env)
        send_tg(env.get("BOT_TOKEN"), env.get("CHAT_ID"),
                f"🚀 LIVE ENABLED: {conf.get('strategy','?')} ({g4.reason})")
        print("[✓] Switched to LIVE")
    elif (not want_live) and cur_live:
        env["DRY_RUN"] = "1"; write_env(env)
        send_tg(env.get("BOT_TOKEN"), env.get("CHAT_ID"), "🔒 Reverted to DRY")
        print("[✓] Reverted to DRY")
    else:
        print(f"[i] State unchanged (DRY_RUN={env.get('DRY_RUN')})")

    # Brief reasons
    for tag,res in [("VPN",g1),("MKT",g2),("RISK",g3),("TTL",g4)]:
        print(f"[{tag}] {'OK' if res.ok else 'X'} - {res.reason}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
