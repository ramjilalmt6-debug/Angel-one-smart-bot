#!/usr/bin/env python3
from __future__ import annotations
import os, csv, json
from pathlib import Path

ROOT = Path.home()/ "angel-one-smart-bot"
DATA = ROOT/ "data"; DATA.mkdir(parents=True, exist_ok=True)

# --- .env ---
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env", override=True)
except Exception:
    pass

def smart_connect():
    try:
        from SmartApi import SmartConnect
    except ModuleNotFoundError:
        from smartapi import SmartConnect
    return SmartConnect

def login():
    cid  = os.getenv("CLIENT_CODE")
    akey = os.getenv("API_KEY")
    mpin = os.getenv("MPIN")
    tsec = os.getenv("TOTP_SECRET")
    if not all([cid, akey, mpin, tsec]):
        return None
    import pyotp
    SC = smart_connect()
    api = SC(api_key=akey)
    api.generateSession(cid, mpin, pyotp.TOTP(tsec).now())
    return api

def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)

def fetch_instruments_via_api(api, exch: str) -> list[dict]:
    if api is None:
        return []
    fns = ("getInstruments","getInstrumentsData","getAllInstruments","instruments","get_instruments","instrumentList")
    for name in fns:
        fn = getattr(api, name, None)
        if callable(fn):
            try:
                try:
                    r = fn(exchange=exch)
                except Exception:
                    r = fn(exch) if getattr(fn, "__code__", None) and fn.__code__.co_argcount>=1 else fn()
                data = r.get("data") if isinstance(r, dict) else r
                if not isinstance(data, list):
                    continue
                rows = []
                for d in data:
                    rows.append({
                        "exchange": d.get("exchange") or exch,
                        "symbol": d.get("symbol") or d.get("tradingsymbol") or d.get("symbolname") or "",
                        "name": d.get("name") or d.get("symbolname") or "",
                        "symboltoken": d.get("symboltoken") or d.get("token") or "",
                        "instrumenttype": d.get("instrumenttype") or d.get("instrument_type") or "",
                        "segment": d.get("segment") or d.get("exch_seg") or "",
                    })
                return rows
            except Exception:
                pass
    return []

def fetch_scrip_master() -> list[dict]:
    """
    Public Angel One Scrip Master JSON (no auth).
    """
    import requests
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Normalize keys
    out = []
    for d in data:
        out.append({
            "exchange": d.get("exch_seg") or d.get("exchange") or "",
            "symbol": d.get("symbol") or d.get("tradingsymbol") or d.get("symbolname") or "",
            "name": d.get("name") or d.get("symbolname") or "",
            "symboltoken": d.get("token") or d.get("symboltoken") or "",
            "instrumenttype": d.get("instrumenttype") or d.get("instrument_type") or "",
            "segment": d.get("exch_seg") or "",
        })
    # save raw for reference
    (DATA/"scrip_master.json").write_text(json.dumps(out, ensure_ascii=False))
    return out

def save_from_master(master: list[dict]):
    # Build per-exchange CSVs from master
    nse = [r for r in master if r["exchange"] == "NSE" and (r["instrumenttype"] or "").upper() != "INDEX"]
    nfo = [r for r in master if r["exchange"] == "NFO"]
    indices = [r for r in master if (r["instrumenttype"] or "").upper() == "INDEX"]
    save_csv(DATA/"instruments_NSE.csv", nse)
    save_csv(DATA/"instruments_NFO.csv", nfo)
    save_csv(DATA/"instruments_INDICES.csv", indices)
    save_csv(DATA/"instruments_NSE_INDICES.csv", indices)

def main():
    api = login()
    counts = {}
    total = 0
    for ex in ("NSE_INDICES","INDICES","NSE","NFO"):
        rows = fetch_instruments_via_api(api, ex)
        counts[ex] = len(rows)
        total += len(rows)
        save_csv(DATA / f"instruments_{ex}.csv", rows)

    if total == 0:
        # API failed/empty -> fallback to public scrip master
        master = fetch_scrip_master()
        save_from_master(master)
        # recount after fallback
        counts = {
            "NSE": sum(1 for _ in (DATA/"instruments_NSE.csv").read_text().splitlines()[1:]) if (DATA/"instruments_NSE.csv").exists() else 0,
            "NFO": sum(1 for _ in (DATA/"instruments_NFO.csv").read_text().splitlines()[1:]) if (DATA/"instruments_NFO.csv").exists() else 0,
            "INDICES": sum(1 for _ in (DATA/"instruments_INDICES.csv").read_text().splitlines()[1:]) if (DATA/"instruments_INDICES.csv").exists() else 0,
            "NSE_INDICES": sum(1 for _ in (DATA/"instruments_NSE_INDICES.csv").read_text().splitlines()[1:]) if (DATA/"instruments_NSE_INDICES.csv").exists() else 0,
        }

    print(json.dumps({"saved_counts": counts, "dir": str(DATA)}))

if __name__ == "__main__":
    main()
