from __future__ import annotations
import os, time, random
import pyotp
from SmartApi.smartConnect import SmartConnect
from SmartApi.smartExceptions import DataException

# Retry-worthy messages (Angel One style)
RL = (
    "Access denied because of exceeding access rate",
    "Too many requests",
    "Request rate limit exceeded",
)

def _rl(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        any(e.lower() in m for e in RL)
        or "couldn't parse the json" in m  # empty/garbled body from server
    )

def login() -> SmartConnect:
    api = os.environ["SMARTAPI_API_KEY"]
    cid = os.environ["SMARTAPI_CLIENT_CODE"]
    pwd = os.environ["SMARTAPI_PASSWORD"]
    totp = pyotp.TOTP(os.environ["TOTP_SECRET"]).now()
    sc = SmartConnect(api)
    sc.generateSession(cid, pwd, totp)
    return sc

def with_retry(fn, tries: int = 6, base: float = 0.6, cap: float = 5.0):
    """Small-burst retries with exponential backoff + jitter (Angel One friendly)."""
    for i in range(tries):
        try:
            return fn()
        except DataException as e:
            if not _rl(str(e)):
                raise
        except Exception:
            pass
        time.sleep(min(cap, base * (2 ** i)) + random.uniform(0, 0.4))
    raise RuntimeError("retry exhausted")

def order_book_safe(sc):
    return with_retry(lambda: sc.orderBook())

def cancel_order_safe(sc, variety, order_id):
    return with_retry(lambda: sc.cancelOrder(variety, order_id))

def place_order_safe(sc, order):
    return with_retry(lambda: sc.placeOrder(order))
