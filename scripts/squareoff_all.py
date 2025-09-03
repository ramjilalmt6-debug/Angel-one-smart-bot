import os, sys

def env(k, d=""):
    v = os.getenv(k, "").strip()
    return v if v else d

def need(k):
    v = env(k)
    if not v:
        raise RuntimeError("Missing env: %s" % k)
    return v

def login():
    from SmartApi import SmartConnect
    import pyotp
    sc = SmartConnect(api_key=need("SMARTAPI_API_KEY"))
    otp = pyotp.TOTP(need("TOTP_SECRET").replace(" ","").upper()).now()
    sc.generateSession(need("SMARTAPI_CLIENT_CODE"), need("SMARTAPI_PASSWORD"), otp)
    return sc

def fetch_positions(sc):
    for fn in ("position", "getPosition"):
        if hasattr(sc, fn):
            try:
                out = getattr(sc, fn)()
                data = (out or {}).get("data") or []
                if isinstance(data, dict):
                    data = data.get("net") or data.get("positiondata") or []
                return data or []
            except Exception:
                pass
    return []

def qty_of(row):
    for k in ("netqty", "netQty", "net_quantity", "netquantity"):
        if k in row:
            try:
                return int(float(str(row[k]).strip()))
            except:
                pass
    return 0

def squareoff_one(sc, row):
    q = qty_of(row)
    if q == 0:
        return "skip: flat"

    prod = (row.get("producttype") or row.get("product") or "").upper()
    if prod != "INTRADAY":
        return "skip: product=%s" % (row.get("producttype") or row.get("product") or "")

    ts = row.get("tradingsymbol") or row.get("symbolname") or ""
    ex = row.get("exchange") or "NSE"
    tok = str(row.get("symboltoken") or row.get("symbol_token") or "").strip()

    side = "SELL" if q > 0 else "BUY"
    qty = str(abs(q))

    order = {
        "variety": "NORMAL",
        "tradingsymbol": ts,
        "symboltoken": tok,
        "transactiontype": side,
        "exchange": ex,
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": "0",
        "quantity": qty,
    }
    try:
        resp = sc.placeOrder(order)
        oid = (resp or {}).get("data", {}).get("orderid") if isinstance(resp, dict) else None
        return "ok: %s %s x%s -> %s" % (order["transactiontype"], ts, qty, oid)
    except Exception as e:
        return "err: %s %s x%s -> %s" % (order["transactiontype"], ts, qty, e)

def main():
    if env("SQUAREOFF_ON_KILL", "0") != "1":
        print("[i] SQUAREOFF_ON_KILL=0; exit")
        return 0
    if env("DRY_RUN", "1") != "1" and env("FORCE_SQUAREOFF", "0") != "1":
        print("[i] DRY_RUN=0; skip (set FORCE_SQUAREOFF=1 to override)")
        return 0

    sc = login()
    rows = fetch_positions(sc)
    any_act = False
    for r in rows:
        msg = squareoff_one(sc, r)
        if not msg.startswith("skip"):
            any_act = True
        print(msg)

    try:
        if hasattr(sc, "logout"):
            sc.logout()
    except Exception:
        pass

    if not any_act:
        print("[i] nothing to square-off")
    return 0

if __name__ == "__main__":
    try:
        import pyotp
        from SmartApi import SmartConnect
    except Exception as e:
        print("[X] deps missing:", e)
        sys.exit(1)

    try:
        sys.exit(main())
    except Exception as e:
        print("[X] squareoff error:", e)
        sys.exit(1)
