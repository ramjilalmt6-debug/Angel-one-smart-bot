import os, time
from scripts.notify import send
from typing import Optional, Tuple

# --- env helpers ---
def env(k, d=""):
    v = os.getenv(k, "").strip()
    return v if v else d

# Config
INDEX = env("INDEX_SYMBOL", "NIFTY")        # NIFTY or BANKNIFTY
EXCH  = env("DERIV_EXCHANGE", "NFO")        # NFO for options
LOT   = int(env("LOT_NIFTY", "75"))         # adjust if using BANKNIFTY etc.
MOMENTUM_PCT = float(env("MOMENTUM_PCT", "0.12"))  # 0.12% 1s move
QTY_LOTS = int(env("QTY_LOTS", "1"))

def round_to_50(x: float) -> int:
    return int(round(x/50.0)*50)

def get_index_token(sc, index_symbol: str) -> Optional[str]:
    try:
        if hasattr(sc, "searchScrip"):
            r = sc.searchScrip("NSE", index_symbol)
            data = (r or {}).get("data") or []
            # pick exact match if present, else first
            for s in data:
                if (s.get("symbolname") or "").upper() == index_symbol.upper():
                    return str(s.get("symboltoken"))
            if data:
                return str(data[0].get("symboltoken"))
    except Exception:
        pass
    return None

def ltp(sc, exchange: str, tradingsymbol: str, token: Optional[str]) -> Optional[float]:
    try:
        if hasattr(sc, "ltpData"):
            r = sc.ltpData(exchange=exchange, tradingsymbol=tradingsymbol, symboltoken=(token or ""))
            p = (r or {}).get("data", {}).get("ltp")
            return float(p) if p is not None else None
    except Exception:
        return None
    return None

def resolve_atm_option(sc, index_symbol: str, spot: float, opt_type: str) -> Tuple[str, str]:
    strike = round_to_50(spot)
    chosen_ts, chosen_tok = "", ""
    try:
        if hasattr(sc, "searchScrip"):
            r = sc.searchScrip(EXCH, index_symbol)
            data = (r or {}).get("data") or []
            for s in data:
                sym = (s.get("tradingsymbol") or s.get("symbolname") or "")
                if str(strike) in sym and sym.endswith(opt_type):
                    chosen_ts = sym
                    chosen_tok = str(s.get("symboltoken") or "")
                    break
    except Exception:
        pass
    if not chosen_ts:  # fallback (may fail if broker requires exact TS)
        chosen_ts = f"{index_symbol}{opt_type}{strike}"
    return chosen_ts, chosen_tok

def get_signal(sc):
    """
    Tiny momentum signal:
      - Poll index LTP twice ~1s apart
      - If +Δ% > threshold → BUY ATM CE
      - If -Δ% > threshold → BUY ATM PE
    Returns an AngelOne placeOrder dict or None.
    """
    idx_tok = get_index_token(sc, INDEX)
    p1 = ltp(sc, "NSE", INDEX, idx_tok)
    time.sleep(1.0)
    p2 = ltp(sc, "NSE", INDEX, idx_tok)
    if not p1 or not p2:
        return None
    chg = (p2 - p1) / p1 * 100.0
    if abs(chg) < MOMENTUM_PCT:
        return None

    opt = "CE" if chg > 0 else "PE"
    ts_opt, tok_opt = resolve_atm_option(sc, INDEX, p2, opt)
    qty = str(max(1, LOT * QTY_LOTS))

    order = {
        "variety": "NORMAL",
        "tradingsymbol": ts_opt,
        "symboltoken": tok_opt,
        "transactiontype": "BUY",
        "exchange": EXCH,
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": "0",
        "quantity": qty,
        "_meta": {"reason": f"momentum {chg:.2f}% on {INDEX}, ATM {opt}", "under": INDEX, "spot": p2},
    }
    return order

from ._template_entry import tick

from ._template_entry import tick as _fallback_tick


def tick(api=None, live=False):
    try:
        return _fallback_tick(api=api, live=live)
    except Exception:
        pass
