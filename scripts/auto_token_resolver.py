from __future__ import annotations
import argparse, csv, json, time, math
from pathlib import Path
from urllib.request import urlopen, Request
from scripts.expiry_calc import parse_hint_to_date, compute_weekly_expiry, compute_monthly_expiry
from core.token_map import get_by_tradingsymbol, get_token

ROOT = Path(__file__).resolve().parents[1]
CSV  = ROOT / "data" / "instruments.csv"
URL  = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

def ensure_csv(max_age_h=18):
    if CSV.exists() and (time.time()-CSV.stat().st_mtime)/3600.0 <= max_age_h:
        return
    req = Request(URL, headers={"User-Agent":"Mozilla/5.0"})
    data = json.loads(urlopen(req, timeout=60).read().decode("utf-8","ignore"))
    rows = data["data"] if isinstance(data, dict) and "data" in data else data
    HEAD = ["token","tradingsymbol","name","exch_seg","instrumenttype","expiry","strike","lotsize"]
    tmp = CSV.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(HEAD); seen=set()
        for r in rows:
            n = {
                "token": str(r.get("token") or r.get("symboltoken") or r.get("instrument_token") or "").strip(),
                "tradingsymbol": str(r.get("symbol") or r.get("tradingsymbol") or "").upper().strip(),
                "name": str(r.get("name") or r.get("underlying") or r.get("underlyingsymbol") or "").upper().strip(),
                "exch_seg": str(r.get("exch_seg") or r.get("exchange") or "NFO").upper().strip(),
                "instrumenttype": str(r.get("instrumenttype") or r.get("instrument_type") or r.get("optiontype") or "").upper().strip(),
                "expiry": str(r.get("expiry") or r.get("expirydate") or r.get("expdate") or "").strip(),
                "strike": str(r.get("strike") or r.get("strikeprice") or "").strip(),
                "lotsize": str(r.get("lotsize") or r.get("lot_size") or r.get("lots") or "").strip(),
            }
            key=(n["token"],n["tradingsymbol"])
            if not n["token"] or not n["tradingsymbol"] or key in seen: continue
            seen.add(key); w.writerow([n[h] for h in HEAD])
    tmp.replace(CSV)

def norm(x): return (x or "").upper().strip()

def nearest_on_same_expiry(symbol:str, expiry:str, opt:str, strike_req:float, exch:str):
    best=None; bestdiff=1e18
    with CSV.open() as f:
        r = csv.DictReader(f)
        for row in r:
            if norm(row.get("name"))!=norm(symbol): continue
            if norm(row.get("exch_seg") or "NFO")!=norm(exch): continue
            if (row.get("expiry") or "") != expiry: continue
            ts = norm(row.get("tradingsymbol"))
            if not ts.endswith(norm(opt)): continue
            try: sr = float(row.get("strike") or 0)
            except: continue
            diff = abs(sr - float(strike_req))
            if diff < bestdiff:
                bestdiff = diff; best = row
    return best

def nearest_across_nearby_expiries(symbol:str, expiry:str, opt:str, strike_req:float, exch:str):
    # Try a small ring: weekly k=0..2, then this-monthly (0) and next-monthly (1)
    exps = []
    try:
        base = parse_hint_to_date(symbol, expiry) if expiry else compute_weekly_expiry(symbol,0)
    except Exception:
        base = compute_weekly_expiry(symbol,0)
    exps.append(base.strftime("%Y-%m-%d"))
    for k in (1,2):
        exps.append(compute_weekly_expiry(symbol,k).strftime("%Y-%m-%d"))
    exps.append(compute_monthly_expiry(symbol,0).strftime("%Y-%m-%d"))
    exps.append(compute_monthly_expiry(symbol,1).strftime("%Y-%m-%d"))

    best=None; bestscore=(None,1e18)  # (expiry, strike_diff)
    with CSV.open() as f:
        rows=list(csv.DictReader(f))
    for e in exps:
        cand=None; diff=1e18
        for row in rows:
            if norm(row.get("name"))!=norm(symbol): continue
            if norm(row.get("exch_seg") or "NFO")!=norm(exch): continue
            if (row.get("expiry") or "") != e: continue
            ts = norm(row.get("tradingsymbol"))
            if not ts.endswith(norm(opt)): continue
            try: sr = float(row.get("strike") or 0)
            except: continue
            d = abs(sr - float(strike_req))
            if d < diff:
                diff = d; cand = row
        if cand and (diff < bestscore[1]):
            best = cand; bestscore=(e,diff)
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts")
    ap.add_argument("--symbol","--name",dest="name")
    ap.add_argument("--expiry")
    ap.add_argument("--strike",type=float)
    ap.add_argument("--opt",choices=["CE","PE"])
    ap.add_argument("--exch",default="NFO")
    ap.add_argument("--nearest",action="store_true")
    ap.add_argument("--max-age-hours",type=int,default=18)
    args = ap.parse_args()

    ensure_csv(args.max_age_hours)

    # Direct TS lookup
    if args.ts:
        c = get_by_tradingsymbol(args.ts)
        print(json.dumps({"error":f"tradingsymbol not found: {args.ts}"} if not c else {
            "token":int(c.token),"tradingsymbol":c.tradingsymbol,"expiry":c.expiry,
            "strike":float(c.strike or 0),"lotsize":int(float(c.lotsize or 0)),"exch":c.exch_seg
        }, ensure_ascii=False))
        return

    # Tuple path
    if not (args.name and args.strike and args.opt):
        print(json.dumps({"error":"Provide --ts OR (--symbol --strike --opt [--expiry])"})); return

    # target expiry
    try:
        exp_dt = parse_hint_to_date(args.name, args.expiry) if args.expiry else compute_weekly_expiry(args.name,0)
    except Exception:
        exp_dt = compute_weekly_expiry(args.name,0)
    exp = exp_dt.strftime("%Y-%m-%d")

    # exact attempt
    tok = get_token(args.name, exp, args.strike, args.opt, args.exch)
    picked_row = None

    # nearest (same expiry)
    if not tok and args.nearest:
        picked_row = nearest_on_same_expiry(args.name, exp, args.opt, args.strike, args.exch)
        if picked_row:
            tok = int(picked_row["token"])

    # nearby-expiry fallback (nearest strike across few upcoming expiries)
    if not tok and args.nearest and not picked_row:
        picked_row = nearest_across_nearby_expiries(args.name, args.expiry or exp, args.opt, args.strike, args.exch)
        if picked_row:
            tok = int(picked_row["token"])

    if not tok:
        print(json.dumps({"error":"No match found","tried":exp}, ensure_ascii=False)); return

    # emit final row (for lotsize etc.)
    if not picked_row:
        with CSV.open() as f:
            r = csv.DictReader(f)
            for row in r:
                if row["token"]==str(tok):
                    picked_row=row; break

    out = {
        "token": int(tok),
        "tradingsymbol": picked_row.get("tradingsymbol") if picked_row else None,
        "expiry": picked_row.get("expiry") if picked_row else exp,
        "strike": float((picked_row or {}).get("strike") or args.strike or 0),
        "lotsize": int(float((picked_row or {}).get("lotsize") or 0)) if picked_row else None,
        "exch": (picked_row or {}).get("exch_seg","NFO")
    }
    if picked_row and (picked_row.get("expiry") != exp or float(picked_row.get("strike") or 0) != float(args.strike)):
        out["fallback_note"] = "picked nearest based on CSV"
    print(json.dumps(out, ensure_ascii=False))
if __name__=="__main__":
    main()
