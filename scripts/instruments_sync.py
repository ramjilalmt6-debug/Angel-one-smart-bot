import json, csv, ssl, urllib.request, time
from pathlib import Path

root = Path.home() / "angel-one-smart-bot"
out  = root / "data" / "instruments.csv"
out.parent.mkdir(parents=True, exist_ok=True)

URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
HEAD= ["token","tradingsymbol","name","exch_seg","instrumenttype","expiry","strike","lotsize"]

ctx = ssl.create_default_context()
with urllib.request.urlopen(URL, context=ctx, timeout=90) as r:
    data = json.loads(r.read().decode("utf-8","ignore"))

rows = data["data"] if isinstance(data, dict) and "data" in data else data
tmp = out.with_suffix(".tmp")
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
tmp.replace(out)
print("[OK] instruments.csv updated:", out)
