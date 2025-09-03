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

def netqty(row):
    for k in ("netqty","netQty","net_quantity","netquantity"):
        if k in row:
            try:
                return int(float(str(row[k]).strip()))
            except:
                pass
    return 0

def pnl(row):
    for k in ("pnl","pnlmtm","unrealized","unrealizedpnl"):
        if k in row:
            try:
                return float(str(row[k]).strip())
            except:
                pass
    return 0.0

def main():
    sc = login()
    rows = fetch_positions(sc)
    lines = []
    for r in rows:
        q = netqty(r)
        ts = r.get("tradingsymbol") or r.get("symbolname") or ""
        prod = (r.get("producttype") or r.get("product") or "").upper()
        if q != 0:
            lines.append(f"{ts} [{prod}] qty={q} pnl={pnl(r):.2f}")

    if not lines:
        msg = "[i] No open positions."
    else:
        msg = "Open positions:\n" + "\n".join(lines)

    print(msg)

    bt, cid = env("BOT_TOKEN"), env("CHAT_ID")
    if bt and cid:
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{bt}/sendMessage",
                data={"chat_id": cid, "text": msg},
                timeout=5,
            )
        except Exception:
            pass

    try:
        if hasattr(sc, "logout"):
            sc.logout()
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    try:
        import pyotp
        from SmartApi import SmartConnect
    except Exception as e:
        print("[X] deps missing:", e)
        sys.exit(1)
    sys.exit(main())
