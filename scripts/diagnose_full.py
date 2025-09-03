#!/usr/bin/env python3
from __future__ import annotations
import os, sys, stat, json, time, subprocess, py_compile, re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

ROOT = Path.home()/ "angel-one-smart-bot"
DATA = ROOT/"data"
ENVF = ROOT/".env"
GUARD = ROOT/"scripts"/"guardian.sh"
NETFIX = ROOT/"scripts"/"net_fix.sh"
AUTOP = ROOT/"scripts"/"autopilot.py"
STRAT_DIR = ROOT/"strategies"

GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; BOLD='\033[1m'; R='\033[0m'
def ok(t):   return f"✅ {t}"
def warn(t): return f"⚠️  {t}"
def bad(t):  return f"❌ {t}"
def c(s,col): return f"{col}{s}{R}"

@dataclass
class Item:
    name: str
    status: str  # PASS/WARN/FAIL
    detail: str
    critical: bool=False

def run(cmd: list[str]):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 127, "", str(e)

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists(): return env
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            k,v=line.split("=",1)
            env[k.strip()]=v.strip()
    return env

def check_python():
    out=[]
    v=sys.version_info
    out.append(Item("Python", "PASS" if v>=(3,10) else "WARN", f"{v.major}.{v.minor}.{v.micro}"))
    venv=ROOT/"venv"
    out.append(Item("Virtualenv", "PASS" if venv.exists() else "FAIL", str(venv), not venv.exists()))
    return out

def check_packages():
    need = ["smartapi-python","requests","schedule","python-dotenv","pyotp","python-telegram-bot"]
    code,out,err = run([sys.executable,"-m","pip","list"])
    have={}
    if code==0:
        for line in out.splitlines():
            parts=line.split()
            if len(parts)>=2: have[parts[0].lower()] = parts[1]
    items=[]
    for p in need:
        v=have.get(p)
        if v: items.append(Item(f"pkg {p}","PASS",v))
        else: items.append(Item(f"pkg {p}","FAIL","missing (pip install -r requirements.txt)",True))
    return items

def check_files():
    items=[]
    # required files
    req = [AUTOP, GUARD, NETFIX, STRAT_DIR/"pcr_momentum_oi.py", ROOT/"core"/"risk.py", ROOT/"scripts"/"notify.py"]
    for fp in req:
        if fp.exists(): items.append(Item(f"{fp.relative_to(ROOT)}","PASS","exists"))
        else: items.append(Item(f"{fp.relative_to(ROOT)}","FAIL","missing",True))
    # exec bits
    for sh in [GUARD, NETFIX]:
        if sh.exists():
            try:
                st=sh.stat().st_mode
                if st & stat.S_IXUSR: items.append(Item(f"exec {sh.name}","PASS","executable"))
                else: items.append(Item(f"exec {sh.name}","WARN","not executable (chmod +x)"))
            except Exception as e:
                items.append(Item(f"exec {sh.name}","WARN",str(e)))
    # autopilot compiles?
    if AUTOP.exists():
        try:
            py_compile.compile(str(AUTOP), doraise=True)
            items.append(Item("autopilot syntax","PASS","py_compile ok"))
        except Exception as e:
            items.append(Item("autopilot syntax","FAIL",str(e),True))
    return items

def check_guardian():
    items=[]
    if not GUARD.exists():
        return [Item("guardian.sh","FAIL","missing",True)]
    txt = GUARD.read_text()
    if "python3 -u scripts/autopilot.py" in txt:
        items.append(Item("guardian launch","PASS","uses python3 -u"))
    elif "python3 scripts/autopilot.py" in txt:
        items.append(Item("guardian launch","WARN","add -u for unbuffered output"))
    else:
        items.append(Item("guardian launch","WARN","autopilot call not found"))
    if "net_fix.sh" in txt:
        items.append(Item("net_fix hook","PASS","present"))
    else:
        items.append(Item("net_fix hook","WARN","guardian not calling net_fix.sh"))
    return items

def check_crontab():
    code,out,err=run(["crontab","-l"])
    if code!=0:
        return [Item("crontab","WARN","no crontab for this user")]
    items=[]
    if "guardian.sh" in out: items.append(Item("crontab guardian","PASS","scheduled"))
    else: items.append(Item("crontab guardian","WARN","missing"))
    if "@reboot" in out and "autopilot.py" in out:
        if "python3 -u" in out: items.append(Item("crontab @reboot","PASS","-u present"))
        else: items.append(Item("crontab @reboot","WARN","use python3 -u for logs"))
    else:
        items.append(Item("crontab @reboot","WARN","add reboot auto-start"))
    return items

def check_env(env: dict):
    items=[]
    if not env:
        return [Item(".env","FAIL",f"Missing or empty: {ENVF}",True)]
    items.append(Item(".env","PASS",str(ENVF)))
    req = ["CLIENT_CODE","API_KEY","MPIN","TOTP_SECRET","LIVE","DRY"]
    miss=[k for k in req if not env.get(k)]
    if miss: items.append(Item("env keys","FAIL","Missing: "+", ".join(miss),True))
    else: items.append(Item("env keys","PASS","core keys present"))
    # telegram optional
    if env.get("TELEGRAM_TOKEN") and env.get("TELEGRAM_CHAT_ID"):
        items.append(Item("telegram env","PASS","token + chat id present"))
    else:
        items.append(Item("telegram env","WARN","token/chat missing (alerts limited)"))
    # perms
    try:
        st=ENVF.stat()
        if st.st_mode & (stat.S_IRWXG|stat.S_IRWXO):
            items.append(Item(".env perms","WARN","world/group readable; run: chmod 600 ~/.env"))
        else:
            items.append(Item(".env perms","PASS","<=600"))
    except Exception as e:
        items.append(Item(".env perms","WARN",str(e)))
    # LIVE/DRY logic
    live=env.get("LIVE","0"); dry=env.get("DRY","1")
    if live==dry:
        items.append(Item("LIVE/DRY","WARN",f"LIVE={live}, DRY={dry} (should differ)"))
    else:
        items.append(Item("LIVE/DRY","PASS",f"LIVE={live}, DRY={dry}"))
    return items

def check_risk(env: dict):
    items=[]
    try:
        cap=float(env.get("CAPITAL","0"))
        per=float(env.get("PER_TRADE","0"))
        lots=int(env.get("LOTS_MAX","0"))
        dsl=float(env.get("DAILY_SL","0"))
        dtp=float(env.get("DAILY_TP","0"))
        assert cap>0 and 0<per<=1 and lots>0 and dsl>0 and dtp>0
        items.append(Item("risk cfg","PASS",f"capital={cap}, per={per}, lots={lots}"))
        # sanity hints
        if per>0.05: items.append(Item("risk per_trade","WARN",f"{per} (>5%)"))
        if dsl>cap*0.1: items.append(Item("risk daily_sl","WARN",f"{dsl} (>10% cap)"))
    except Exception as e:
        items.append(Item("risk cfg","FAIL","invalid/missing",True))
    # NSE lots baseline
    base={"NIFTY50":75,"BANKNIFTY":35,"FINNIFTY":65,"MIDCPNIFTY":140}
    dif=[]
    for k,exp in base.items():
        v=env.get(f"LOT_{k}")
        if v:
            try:
                if int(v)!=exp: dif.append(f"{k}={v} (!={exp})")
            except: pass
    if dif: items.append(Item("lot sizes","WARN",", ".join(dif)))
    else: items.append(Item("lot sizes","PASS","matches 2025 baseline or unset"))
    return items

def check_ip(env: dict):
    want = (env.get("DEDICATED_IP") or "").strip()
    try:
        import urllib.request
        actual = urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode()
        if want and actual == want:
            return [Item("public IP lock","PASS",f"{actual} == expected")]
        elif want:
            return [Item("public IP lock","FAIL",f"{actual} != expected {want}",True)]
        else:
            return [Item("public IP lock","WARN",f"no DEDICATED_IP set (actual {actual})")]
    except Exception as e:
        return [Item("public IP lock","WARN",f"Could not fetch ({e})")]

def check_process_and_logs():
    items=[]
    code,out,err=run(["pgrep","-af","python3 .*scripts/autopilot.py"])
    if code==0 and out:
        items.append(Item("autopilot process","PASS",out.splitlines()[0]))
    else:
        items.append(Item("autopilot process","WARN","not running"))
    # logs
    ap_log = DATA/"autopilot.out"
    if ap_log.exists():
        try:
            mtime = datetime.fromtimestamp(ap_log.stat().st_mtime)
            age = datetime.now() - mtime
            if age <= timedelta(minutes=10):
                items.append(Item("autopilot.out mtime","PASS",f"updated {int(age.total_seconds()/60)} min ago"))
            else:
                items.append(Item("autopilot.out mtime","WARN",f"stale ({int(age.total_seconds()/60)} min)"))
            txt = ap_log.read_text()[-5000:]
            ok_seen = "login_ok" in txt
            if ok_seen:
                items.append(Item("login_ok in log","PASS","seen in recent log"))
            else:
                items.append(Item("login_ok in log","WARN","not seen in tail; check earlier/full log"))
            if "strategy_error" in txt:
                items.append(Item("strategy errors","WARN","found in tail; inspect logs"))
        except Exception as e:
            items.append(Item("autopilot.out","WARN",str(e)))
    else:
        items.append(Item("autopilot.out","WARN","missing (will be created on first run)"))
    return items

def check_strategies():
    items=[]
    if not STRAT_DIR.exists():
        return [Item("strategies","FAIL","folder missing",True)]
    ss=[p for p in STRAT_DIR.glob("*.py") if p.name!="__init__.py"]
    if not ss:
        return [Item("strategies","FAIL","no .py strategies",True)]
    for s in ss:
        txt=s.read_text()
        have=[fn for fn in ("tick","run","main") if re.search(rf"def\s+{fn}\s*\(", txt)]
        if have:
            items.append(Item(f"strategy {s.name}","PASS","has: "+",".join(have)))
        else:
            items.append(Item(f"strategy {s.name}","WARN","no tick/run/main found"))
    return items

def check_timezone():
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        return [Item("timezone","PASS",f"Asia/Kolkata ok ({now:%Y-%m-%d %H:%M})")]
    except Exception as e:
        return [Item("timezone","FAIL",str(e),True)]

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    env = load_env(ENVF)

    items=[]
    items+=check_python()
    items+=check_packages()
    items+=check_files()
    items+=check_guardian()
    items+=check_crontab()
    items+=check_env(env)
    items+=check_risk(env)
    items+=check_ip(env)
    items+=check_process_and_logs()
    items+=check_strategies()
    items+=check_timezone()

    crit=0; warns=0
    print("\n"+"="*72)
    print(c("Angel One Autopilot — FULL Diagnostic", BOLD))
    print("="*72+"\n")
    for it in items:
        if it.status=="PASS": print(ok(f"{it.name}: {it.detail}"))
        elif it.status=="WARN": print(warn(f"{it.name}: {it.detail}")); warns+=1
        else:
            print(bad(f"{it.name}: {it.detail}"))
            if it.critical: crit+=1

    print("\n"+"-"*72)
    if crit==0:
        print(c("SUMMARY: READY (no critical failures) ✅", GREEN))
    else:
        print(c(f"SUMMARY: NOT READY (critical failures: {crit}) ❌", RED))
    if warns:
        print(c(f"Notes: {warns} warnings (non-blocking).", YEL))
    print("-"*72)

    # Tail helpful context if available
    ap_log = DATA/"autopilot.out"
    if ap_log.exists():
        print("\nLast log tail (autopilot.out):")
        try:
            txt = ap_log.read_text().splitlines()[-20:]
            for ln in txt: print(ln)
        except Exception as e:
            print(f"[tail error] {e}")
    return 0 if crit==0 else 2

if __name__=="__main__":
    sys.exit(main())
