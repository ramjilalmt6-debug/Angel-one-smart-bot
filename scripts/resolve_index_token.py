#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re
from pathlib import Path

ROOT = Path.home()/ "angel-one-smart-bot"
DATA = ROOT/ "data"

def scan(files, patterns):
    picks = []
    for fp in files:
        if not fp.exists(): 
            continue
        with fp.open() as f:
            r = csv.DictReader(f)
            for row in r:
                name = (row.get("name") or row.get("symbol") or "").strip()
                sym  = (row.get("symbol") or row.get("tradingsymbol") or "").strip()
                exch = (row.get("exchange") or "").strip()
                tok  = (row.get("symboltoken") or row.get("token") or "").strip()
                text = f"{name} {sym}".lower()
                if not tok: 
                    continue
                for label, rx in patterns:
                    if rx.search(text):
                        score = 0
                        if "index" in text: score += 2
                        if "nifty" in text: score += 1
                        if "bank"  in text: score += 1
                        if exch in ("NSE_INDICES","INDICES"): score += 1
                        picks.append({"label":label,"exchange":exch,"token":tok,"symbol":sym,"name":name,"score":score,"file":fp.name})
    picks.sort(key=lambda x: (-x["score"], x["exchange"], x["name"]))
    return picks[:10]

def main():
    files = [
        DATA/"instruments_NSE_INDICES.csv",
        DATA/"instruments_INDICES.csv",
        DATA/"instruments_NSE.csv",
        DATA/"instruments_NFO.csv",
    ]
    patterns = [
        ("NIFTY_50", re.compile(r"\bnifty\b.*\b50\b|\bnifty50\b")),
        ("NIFTY_BANK", re.compile(r"\bnifty\b.*\bbank\b|\bbanknifty\b")),
    ]
    out = scan(files, patterns)
    print(json.dumps({"candidates": out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
