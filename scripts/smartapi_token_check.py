from __future__ import annotations
import os, sys, subprocess
from dataclasses import dataclass

try:
    from SmartApi import SmartConnect  # smartapi-python
except Exception as e:
    print("[X] smartapi-python import failed:", e)
    sys.exit(1)

def env_str(k: str) -> str:
    v = os.getenv(k, "").strip()
    if not v:
        raise RuntimeError(f"Missing env: {k}")
    return v

@dataclass(frozen=True)
class Creds:
    api_key: str
    client_code: str
    password: str
    totp_secret: str

def load_creds() -> Creds:
    return Creds(
        api_key=env_str("SMARTAPI_API_KEY"),
        client_code=env_str("SMARTAPI_CLIENT_CODE"),
        password=env_str("SMARTAPI_PASSWORD"),
        totp_secret=env_str("TOTP_SECRET"),
    )

def assert_vpn_lock() -> None:
    want = os.getenv("NORDVPN_REQUIRED_IP", "").strip()
    if not want:
        return
    try:
        ip = subprocess.check_output(
            ["bash","-lc","curl -s https://ifconfig.me || true"], timeout=8
        ).decode().strip()
    except Exception:
        ip = ""
    if ip != want:
        raise RuntimeError(f"VPN IP mismatch: got {ip!r}, want {want!r}")

def current_otp(secret: str) -> str:
    import pyotp
    return pyotp.TOTP(secret.replace(" ","").upper()).now()

def main() -> int:
    try:
        creds = load_creds()
        assert_vpn_lock()
        otp = current_otp(creds.totp_secret)
        print(f"[i] Using OTP: {otp}")

        sc = SmartConnect(api_key=creds.api_key)

        # Login → capture tokens
        resp = sc.generateSession(creds.client_code, creds.password, otp)
        if not isinstance(resp, dict) or "data" not in resp:
            raise RuntimeError(f"generateSession unexpected: {resp}")
        data = resp.get("data") or {}
        jwt  = data.get("jwtToken")
        rtok = data.get("refreshToken")
        feed = data.get("feedToken")
        print("[✓] Session generated")
        print(f"[i] Tokens: jwt={'yes' if jwt else 'no'}, refresh={'yes' if rtok else 'no'}, feed={'yes' if feed else 'no'}")

        # Profile (newer lib requires refreshToken)
        try:
            if rtok:
                prof = sc.getProfile(rtok)
            else:
                # fallback: some builds accept without arg (unlikely)
                prof = sc.getProfile()
            u = (prof or {}).get("data", {})
            print(f"[✓] Profile OK: name={u.get('name','?')} id={u.get('clientcode','?')}")
        except TypeError as te:
            print(f"[!] getProfile signature mismatch: {te}")
        except Exception as e:
            print("[!] getProfile failed:", e)

        # Logout / Terminate (handle multiple lib variants)
        try:
            if hasattr(sc, "logout"):
                out = sc.logout()
                print("[✓] Logout success" if getattr(out, "get", lambda *_: None)("status") else f"[i] Logout resp: {out}")
            elif hasattr(sc, "terminateSession"):
                # Some versions want client code, some want jwt/rtok — try client_code first
                try:
                    out = sc.terminateSession(creds.client_code)
                except Exception:
                    out = sc.terminateSession(jwt or rtok or "")
                print("[✓] Session terminated" if str(out).lower().find("success")!=-1 else f"[i] Terminate resp: {out}")
            else:
                print("[i] No logout/terminate method in this SmartApi build; skipping")
        except Exception as e:
            print("[i] Logout/terminate error (ignored):", e)

        return 0
    except Exception as e:
        print("[X] SmartAPI token check failed:", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
