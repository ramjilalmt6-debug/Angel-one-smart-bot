#!/usr/bin/env python3
"""
Angel One Autopilot — Mini Diagnostic (safe)
Checks:
 1) Python & venv
 2) Packages
 3) Project files & exec bit for guardian/net_fix
 4) .env mandatory keys + perms + LIVE/DRY sanity
 5) Risk sanity + 2025 lot sizes
 6) Public IP lock (expects DEDICATED_IP=89.117.176.75)
 7) Cron mentions guardian.sh/autopilot.py
 8) Timezone IST + optional holidays file
 9) Telegram token/chat presence
"""
from __future__ import annotations
import sys, os, stat, json, subprocess
from pathlib import Path
from dataclasses import dataclass

GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; BOLD="\033[1m"; R="\033[0m"
def C(s,c): return f"{c}{s}{R}"
def OK(t): return f"✅ {t}"
def WR(t): return f"⚠️  {t}"
def NG(t): return f"❌ {t}"

@dataclass
class Item:
    name: str
    status: str  # PASS/WARN/FAIL
    detail: str
    critical: bool=False

def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 127, "", str(e)

def load_env(p: Path):
    env={}
    if p.exists():
        for line in p.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                k,v=line.split("=",1); env[k.strip()]=v.strip()
    return env

def check_python(root: Path):
    out=[]
    ver=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    out.append(Item("Python", "PASS" if sys.version_info >= (3,10) else "WARN", f"{ver}"))
    venv=root/"venv"
    out.append(Item("venv", "PASS" if venv.exists() else "FAIL", str(venv), not venv.exists()))
    return out

def check_packages():
    need=["smartapi-python","requests","schedule","python-dotenv","pyotp","python-telegram-bot"]
    code,out,_=run([sys.executable,"-m","pip","list"])
    have={}
    if code==0:
        for ln in out.splitlines():
            parts=ln.split()
            if len(parts)>=2: have[parts[0].lower()]=parts[1]
    res=[]
    for p in need:
        v=have.get(p)
        if v: res.append(Item(f"pkg {p}","PASS",v))
        else: res.append(Item(f"pkg {p}","FAIL","not installed (pip install -r requirements.txt)", True))
    return res

def check_tree(root: Path):
    req=[root/"scripts"/"autopilot.py",
         root/"scripts"/"guardian.sh",
         root/"scripts"/"net_fix.sh",
         root/"strategies"/"pcr_momentum_oi.py",
         root/"core"/"risk.py"]
    res=[]
    for fp in req:
        exists = fp.exists()
        res.append(Item(str(fp.relative_to(root)), "PASS" if exists else "FAIL", "exists" if exists else "missing", not exists))
    for sh in [root/"scripts"/"guardian.sh", root/"scripts"/"net_fix.sh"]:
        if sh.exists():
            try:
                execbit = bool(sh.stat().st_mode & stat.S_IXUSR)
                res.append(Item(f"exec {sh.name}", "PASS" if execbit else "WARN", "executable" if execbit else "chmod +x"))
            except Exception as e:
                res.append(Item(f"exec {sh.name}", "WARN", str(e)))
    (root/"data").mkdir(parents=True, exist_ok=True)
    return res

def check_env(env: dict, envp: Path):
    res=[]
    if not env:
        return [Item(".env","FAIL",f"Missing or empty: {envp}", True)]
    res.append(Item(".env","PASS",str(envp)))
    need=["CLIENT_CODE","API_KEY","API_SECRET","MPIN","TOTP_SECRET","CAPITAL","PER_TRADE","LOTS_MAX","DAILY_SL","DAILY_TP","TELEGRAM_TOKEN","TELEGRAM_CHAT_ID"]
    miss=[k for k in need if not env.get(k)]
    res.append(Item("env keys","PASS" if not miss else "FAIL","all present" if not miss else "Missing: "+", ".join(miss), bool(miss)))
    try:
        st=envp.stat()
        if st.st_mode & (stat.S_IRWXG|stat.S_IRWXO):
            res.append(Item(".env perms","WARN","world/group readable; run: chmod 600 ~/.env"))
        else:
            res.append(Item(".env perms","PASS","<=600"))
    except Exception as e:
        res.append(Item(".env perms","WARN",str(e)))
    live=env.get("LIVE","0"); dry=env.get("DRY","1")
    if live=="1" and dry=="1":
        res.append(Item("LIVE/DRY","WARN","Both 1; set DRY=0 when LIVE=1"))
    else:
        res.append(Item("LIVE/DRY","PASS",f"LIVE={live}, DRY={dry}"))
    return res

def check_risk(env: dict):
    res=[]
    try:
        capital=float(env.get("CAPITAL","0"))
        per=float(env.get("PER_TRADE","0"))
        lots=int(env.get("LOTS_MAX","0"))
        dsl=float(env.get("DAILY_SL","0"))
        dtp=float(env.get("DAILY_TP","0"))
        assert capital>0 and 0<per<=1 and lots>0 and dsl>0 and dtp>0
        res.append(Item("risk","PASS",f"capital={capital}, per={per}, lots_max={lots}"))
        base={"NIFTY50":75,"BANKNIFTY":35,"FINNIFTY":65,"MIDCPNIFTY":140}
        mm=[]
        for k,exp in base.items():
            v=env.get(f"LOT_{k}")
            if v:
                try:
                    iv=int(v)
                    if iv!=exp: mm.append(f"{k}={iv} (!={exp})")
                except: pass
        res.append(Item("lot sizes","PASS" if not mm else "WARN", "match 2025 baseline" if not mm else ", ".join(mm)))
    except Exception as e:
        res.append(Item("risk","FAIL",f"invalid ({e})", True))
    return res

def check_ip(env: dict):
    want=env.get("DEDICATED_IP","89.117.176.75").strip()
    try:
        import urllib.request
        actual=urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode()
        if actual==want: return [Item("public IP lock","PASS",f"{actual} == expected")]
        else: return [Item("public IP lock","FAIL",f"{actual} != {want}", True)]
    except Exception as e:
        return [Item("public IP lock","WARN",f"skip/failed: {e}")]

def check_cron():
    code,out,_=run(["crontab","-l"])
    if code!=0: return [Item("crontab","WARN","no crontab for this user")]
    miss=[x for x in ["guardian.sh","autopilot.py"] if x not in out]
    if miss: return [Item("crontab","WARN","missing: "+", ".join(miss))]
    return [Item("crontab","PASS","guardian + autopilot scheduled")]

def check_tz_and_holidays(root: Path):
    res=[]
    try:
        import datetime as dt
        from zoneinfo import ZoneInfo
        now=dt.datetime.now(ZoneInfo("Asia/Kolkata"))
        res.append(Item("timezone","PASS",f"IST ok ({now:%Y-%m-%d %H:%M})"))
    except Exception as e:
        res.append(Item("timezone","FAIL",str(e), True))
    hol=root/"data"/"nse_holidays.json"
    if hol.exists():
        try:
            data=json.loads(hol.read_text())
            res.append(Item("holidays","PASS",f"{len(data)} entries"))
        except Exception as e:
            res.append(Item("holidays","WARN",f"bad JSON ({e})"))
    else:
        res.append(Item("holidays","WARN","nse_holidays.json missing (optional)"))
    return res

def check_telegram(env: dict):
    if env.get("TELEGRAM_TOKEN") and env.get("TELEGRAM_CHAT_ID"):
        return [Item("telegram","PASS","token + chat id")]
    return [Item("telegram","WARN","token/chat missing (alerts off)")]

def main():
    root=Path.home()/ "angel-one-smart-bot"
    envp=root/".env"; env=load_env(envp)
    items=[]
    items+=check_python(root)
    items+=check_packages()
    items+=check_tree(root)
    items+=check_env(env, envp)
    items+=check_risk(env)
    items+=check_ip(env)
    items+=check_cron()
    items+=check_tz_and_holidays(root)
    items+=check_telegram(env)

    crit=0; warn=0
    print("\n"+("="*64))
    print(C("Angel One Autopilot — Mini Diagnostic", BOLD))
    print(("="*64)+"\n")
    for it in items:
        if it.status=="PASS": print(OK(f"{it.name}: {it.detail}"))
        elif it.status=="WARN": print(WR(f"{it.name}: {it.detail}")); warn+=1
        else: print(NG(f"{it.name}: {it.detail}"))
        if it.status=="FAIL" and it.critical: crit+=1
    print("\n"+("-"*64))
    if crit==0: print(C("SUMMARY: READY (no critical failures)", GREEN))
    else: print(C(f"SUMMARY: NOT READY (critical failures: {crit})", RED))
    if warn: print(C(f"Notes: {warn} warnings (non-blocking).", YELLOW))
    print("-"*64)
    print("\nFix hints:")
    print(" • IP mismatch: connect NordVPN dedicated IP, run guardian.sh")
    print(" • Missing pkgs: . venv/bin/activate && pip install -r requirements.txt")
    print(" • Secrets: chmod 600 ~/.env")
    print(" • Autostart: add crontab for guardian + autopilot")
    return 0 if crit==0 else 2

if __name__=="__main__":
    sys.exit(main())
