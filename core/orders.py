from __future__ import annotations
from typing import Dict, Any

def build_market_order(*, tradingsymbol:str, token:int, exch:str, txn:str, qty:int, product:str="INTRADAY") -> Dict[str,Any]:
    return {
        "variety": "NORMAL",
        "tradingsymbol": tradingsymbol,
        "symboltoken": str(token),
        "transactiontype": txn,           # "BUY" or "SELL"
        "exchange": exch,                 # "NFO" or "NSE"
        "ordertype": "MARKET",
        "producttype": product,           # "INTRADAY" | "DELIVERY" | "CARRYFORWARD"
        "duration": "DAY",
        "quantity": int(qty),
    }
