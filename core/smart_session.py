from __future__ import annotations
import os, time
import pyotp
from logzero import logger

# Prefer SmartApi.smartConnect (present in your venv), fallback to smartapi
try:
    from SmartApi.smartConnect import SmartConnect
except ModuleNotFoundError:
    from smartapi import SmartConnect  # fallback if available

API_KEY   = os.getenv("SMARTAPI_SECRET") or os.getenv("SMARTAPI_APIKEY") or os.getenv("SMARTAPI_KEY")
CLIENT_ID = os.getenv("SMARTAPI_CLIENT")
PWD       = os.getenv("SMARTAPI_PWD")
TOTP_SEC  = os.getenv("SMARTAPI_TOTP_SECRET")

class SmartSession:
    def __init__(self):
        self.sc = None; self.jwt = None; self.refresh = None; self.feed = None; self.last_login = 0

    def login(self, force: bool = False):
        if not force and self.jwt and (time.time() - self.last_login < 6*3600):
            return self.jwt
        if not (API_KEY and CLIENT_ID and PWD and TOTP_SEC):
            raise RuntimeError("Missing SmartAPI env: SMARTAPI_SECRET/CLIENT/PWD/TOTP_SECRET")

        self.sc = SmartConnect(API_KEY)
        otp = pyotp.TOTP(TOTP_SEC).now()
        resp = self.sc.generateSession(CLIENT_ID, PWD, otp)

        if not isinstance(resp, dict) or not resp.get("status"):
            raise RuntimeError(f"Login failed: {resp}")
        data = resp.get("data") or {}
        self.jwt = data.get("jwtToken"); self.refresh = data.get("refreshToken")
        self.feed = getattr(self.sc, "getfeedToken", getattr(self.sc, "getFeedToken", lambda: None))()
        self.last_login = time.time()
        logger.info("SmartAPI login ok")
        return self.jwt

    def ensure(self):
        if self.last_login and time.localtime(self.last_login).tm_mday != time.localtime().tm_mday:
            self.login(force=True)
        elif not self.jwt:
            self.login(force=True)
        return self.sc
