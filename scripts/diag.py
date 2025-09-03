from __future__ import annotations
import os, sys, json, importlib, platform
out = {"python": sys.version.split()[0], "errors": [], "checks": {}}

def mark(k, ok, msg=""):
    out["checks"][k] = {"ok": bool(ok), "msg": msg}

# env
ENV = {k: os.getenv(k, "") for k in [
    "CAPITAL","RISK_PCT","LOTS_MAX","LOT_SIZE","MAX_LOSS","MAX_PROFIT",
    "VPN_IP","LIVE","TELEGRAM_TOKEN","TELEGRAM_CHAT_ID"
]}
out["env"] = ENV

# packages
req = ["requests","pandas","schedule","python-dotenv","python-telegram-bot","smartapi-python"]
for m in req:
    try:
        importlib.import_module(m)
        mark(f"pkg:{m}", True)
    except Exception as e:
        mark(f"pkg:{m}", False, str(e))
        out["errors"].append(f"Package {m}: {e}")

# smartapi smoke
try:
    from smartapi import SmartConnect  # type: ignore
    mark("smartapi_import", True)
except Exception as e:
    mark("smartapi_import", False, str(e))
    out["errors"].append(f"smartapi import: {e}")

# strategy load (optional)
ok_strat, err = True, ""
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, base)
try:
    if os.path.exists(os.path.join(base, "strategies", "pcr_momentum_oi.py")):
        import strategies.pcr_momentum_oi as _  # type: ignore
    mark("strategy_import", True, "")
except Exception as e:
    ok_strat, err = False, str(e)
    mark("strategy_import", False, err)

# lot sizing sanity
def fnum(s, d): 
    try: return float(s)
    except: return d

cap = fnum(ENV.get("CAPITAL"), 200000.0)
rp  = fnum(ENV.get("RISK_PCT"), 0.02)
lot = int(float(ENV.get("LOT_SIZE") or 75))
prem_samples = [120, 240, 400]
calc = []
for prem in prem_samples:
    if prem <= 0 or lot <= 0:
        lots = 0
    else:
        units = (cap*rp)/(prem*lot)
        lots = int(max(1, units))
    calc.append({"premium": prem, "lots": lots})
out["lot_calc"] = {"cap": cap, "risk_pct": rp, "lot_size": lot, "samples": calc}

out["platform"] = {"machine": platform.machine(), "system": platform.system()}
print(json.dumps(out, ensure_ascii=False))
