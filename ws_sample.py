from SmartApi.smartConnect import SmartConnect
import os, pyotp

API_KEY   = os.getenv("SMARTAPI_SECRET")
CLIENT_ID = os.getenv("SMARTAPI_CLIENT")
PWD       = os.getenv("SMARTAPI_PWD")
TOTP_SEC  = os.getenv("SMARTAPI_TOTP_SECRET")

print("Env OK?", all([API_KEY, CLIENT_ID, PWD, TOTP_SEC]))

def login():
    sc = SmartConnect(API_KEY)
    totp = pyotp.TOTP(TOTP_SEC).now()
    data = sc.generateSession(CLIENT_ID, PWD, totp)
    print("Login status:", data.get("status"), data.get("message"))
    return sc

if __name__ == "__main__":
    login()
