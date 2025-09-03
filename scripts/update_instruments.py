from __future__ import annotations
import csv, json, sys, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "instruments.csv"
TMP = ROOT / "data" / "instruments.csv.tmp"
LOG = ROOT / "data" / "update-instruments.log"

HEAD = ["token","tradingsymbol","name","exch_seg","instrumenttype","expiry","strike","lotsize"]

SOURCES = [
    # Public, no-auth dump (Angel One margin calculator OpenAPI file)
    # Known in forum/docs as the master list for tokens
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
    # Some mirrors occasionally appear; keep one slot reserved for future if needed
]

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text((LOG.read_text() if LOG.exists() else "") + f"[{ts}] {msg}\n")

def fetch_json(url: str) -> Any:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

def normalize(row: Dict[str, Any]) -> Dict[str, Any]:
    # Accept a variety of keys from different dumps
    return {
        "token": str(row.get("token") or row.get("symboltoken") or row.get("instrument_token") or "").strip(),
        "tradingsymbol": str(row.get("symbol") or row.get("tradingsymbol") or "").upper().strip(),
        "name": str(row.get("name") or row.get("underlying") or row.get("underlyingsymbol") or "").upper().strip(),
        "exch_seg": str(row.get("exch_seg") or row.get("exchange") or "").upper().strip(),
        "instrumenttype": str(row.get("instrumenttype") or row.get("instrument_type") or row.get("optiontype") or "").upper().strip(),
        "expiry": str(row.get("expiry") or row.get("expirydate") or row.get("expdate") or "").strip(),
        "strike": str(row.get("strike") or row.get("strikeprice") or "").strip(),
        "lotsize": str(row.get("lotsize") or row.get("lot_size") or row.get("lots") or "").strip(),
    }

def write_csv(rows: List[Dict[str, Any]]):
    TMP.parent.mkdir(parents=True, exist_ok=True)
    with TMP.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        seen = set()
        for r in rows:
            n = normalize(r)
            key = (n["token"], n["tradingsymbol"])
            if not n["token"] or not n["tradingsymbol"] or key in seen:
                continue
            seen.add(key)
            w.writerow([n[h] for h in HEAD])
    TMP.replace(OUT)

def main():
    try:
        log("Starting instruments update via public Scrip Master")
        data = None
        err = None
        for u in SOURCES:
            try:
                data = fetch_json(u)
                if data:
                    log(f"Fetched source: {u}, type={type(data)}")
                    break
            except Exception as e:
                err = e
                log(f"Fetch failed from {u}: {e}")
        if data is None:
            raise RuntimeError(f"All sources failed: {err}")

        # Some dumps wrap list in {'data': [...]}
        rows = data["data"] if isinstance(data, dict) and "data" in data else data
        if not isinstance(rows, list):
            raise RuntimeError(f"Unexpected JSON format: {type(rows)}")

        log(f"Fetched {len(rows)} raw rows")
        write_csv(rows)
        log(f"Wrote {OUT}")
        print("[OK] instruments.csv updated")
    except Exception as e:
        log(f"ERROR: {e}")
        print(f"[WARN] instruments update failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
