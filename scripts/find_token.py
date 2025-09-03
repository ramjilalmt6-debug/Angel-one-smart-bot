#!/usr/bin/env python3
from __future__ import annotations
import os, json, itertools
from pathlib import Path

# .env
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

def search_variants(q: str) -> list[str]:
    q = (q or "").strip()
    if not q:
        return []
    base = [q]
    ql = q.lower()
    if "nifty" in ql and "bank" not in ql:
        base += ["NIFTY", "NIFTY50", "NIFTY 50", "NSE NIFTY 50", "Nifty 50"]
    if ("nifty" in ql and "bank" in ql) or "banknifty" in ql:
        base += ["NIFTY BANK", "BANKNIFTY", "NSE NIFTY BANK", "Nifty Bank"]
    return list(dict.fromkeys(base))  # de-dupe, keep order

def main():
    try:
        q_in = os.environ.get("Q", "NIFTY 50").strip()
        queries = search_variants(q_in) or [q_in]
        exchs = os.environ.get("EXCHS", "NSE_INDICES,INDICES,NSE,NFO").split(",")
        exchs = [e.strip() for e in exchs if e.strip()]
        # login
        cid  = os.getenv("CLIENT_CODE"); akey = os.getenv("API_KEY")
        mpin = os.getenv("MPIN");        tsec = os.getenv("TOTP_SECRET")
        if not all([cid, akey, mpin, tsec]):
            raise SystemExit("SmartAPI creds missing in .env")

        import pyotp
        SC  = smart_connect()
        otp = pyotp.TOTP(tsec).now()
        api = SC(api_key=akey)
        api.generateSession(cid, mpin, otp)

        # different client versions use different names
        fn_names = ("searchScrip", "search_symbol", "searchScrips", "searchSymbol")

        seen = set()
        rows = []
        for fn_name, ex, q in itertools.product(fn_names, exchs, queries):
            f = getattr(api, fn_name, None)
            if not callable(f): 
                continue
            try:
                # try with exchange kw first; if fails, try plain
                try:
                    r = f(exchange=ex, searchtext=q)
                except Exception:
                    r = f(q)
                data = r.get("data") if isinstance(r, dict) else r
                if not isinstance(data, list):
                    continue
                for d in data:
                    exch = d.get("exchange") or ex
                    sym  = d.get("symbol") or d.get("tradingsymbol") or d.get("symbolname") or ""
                    name = d.get("name") or d.get("symbolname") or sym
                    tok  = d.get("symboltoken") or d.get("token") or ""
                    key  = (exch, tok, sym)
                    if not tok or key in seen:
                        continue
                    # prefer obvious index hits
                    score = 0
                    tl = name.lower() + " " + sym.lower()
                    if "index" in tl or "nse indices" in exch.lower() or exch in ("NSE_INDICES","INDICES"):
                        score += 2
                    if "nifty" in tl: score += 1
                    if "bank" in tl:  score += 1
                    rows.append({
                        "exchange": exch, "symbol": sym, "name": name, "token": tok, "score": score
                    })
                    seen.add(key)
            except Exception:
                pass

        # sort: higher score first, then by exchange preference
        pref = {e:i for i,e in enumerate(["NSE_INDICES","INDICES","NSE","NFO"])}
        rows.sort(key=lambda r: (-r["score"], pref.get(r["exchange"], 99), r["name"]))

        print(json.dumps({"query": q_in, "variants": queries, "exchanges": exchs, "results": rows[:20]}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
