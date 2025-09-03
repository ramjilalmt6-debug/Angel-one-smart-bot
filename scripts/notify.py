#!/usr/bin/env python3
import os, json, urllib.parse, urllib.request, subprocess, shutil
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path.home()/ "angel-one-smart-bot"/ ".env", override=True)

except Exception:
    # Fallback: manually parse .env if python-dotenv not present
    try:
        envp = Path.home()/ "angel-one-smart-bot"/ ".env"
        if envp.exists():
            for line in envp.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k,v = line.split("=",1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT  = os.getenv("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage" if TOKEN else None

def _via_urllib(text: str) -> (bool, str):
    if not API_URL or not CHAT:
        return False, "env_missing"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    try:
        with urllib.request.urlopen(API_URL, data, timeout=10) as r:
            body = r.read().decode("utf-8", "ignore")
            ok = (r.status == 200) and (json.loads(body).get("ok") is True)
            return ok, "urllib_ok" if ok else f"urllib_bad_status:{r.status}"
    except Exception as e:
        return False, f"urllib_exc:{type(e).__name__}"

def _via_requests(text: str) -> (bool, str):
    if not API_URL or not CHAT:
        return False, "env_missing"
    try:
        import requests  # may not exist
    except Exception:
        return False, "requests_missing"
    try:
        resp = requests.post(API_URL, data={"chat_id": CHAT, "text": text}, timeout=10)
        try_insecure = resp.status_code != 200 or not resp.json().get("ok")
        if try_insecure:
            resp = requests.post(API_URL, data={"chat_id": CHAT, "text": text}, timeout=10, verify=False)
        j = {}
        try:
            j = resp.json()
        except Exception:
            pass
        ok = (resp.status_code == 200) and bool(j.get("ok"))
        return ok, "requests_ok" if ok else f"requests_bad:{resp.status_code}"
    except Exception as e:
        return False, f"requests_exc:{type(e).__name__}"

def _via_curl(text: str) -> (bool, str):
    if not API_URL or not CHAT:
        return False, "env_missing"
    curl = shutil.which("curl") or "/data/data/com.termux/files/usr/bin/curl"
    if not Path(curl).exists():
        return False, "curl_missing"
    args = [curl, "-sS", "-X", "POST", API_URL, "-d", f"chat_id={CHAT}", "-d", f"text={text}"]
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=10)
        if cp.returncode != 0 or not cp.stdout.strip():
            # Try with --insecure in case of CA issue
            args_insec = args[:]
            args_insec.insert(2, "--insecure")
            cp = subprocess.run(args_insec, capture_output=True, text=True, timeout=10)
        try:
            j = json.loads(cp.stdout or "{}")
        except Exception:
            j = {}
        ok = bool(j.get("ok"))
        return ok, "curl_ok" if ok else f"curl_bad_rc:{cp.returncode}"
    except Exception as e:
        return False, f"curl_exc:{type(e).__name__}"

def send(text: str) -> bool:
    for fn in (_via_urllib, _via_requests, _via_curl):
        ok, _ = fn(text)
        if ok:
            return True
    return False

if __name__ == "__main__":
    reasons = []
    ok, r = _via_urllib("🔔 notify.py self-test (urllib)")
    reasons.append(r)
    if not ok:
        ok, r = _via_requests("🔔 notify.py self-test (requests)")
        reasons.append(r)
    if not ok:
        ok, r = _via_curl("🔔 notify.py self-test (curl)")
        reasons.append(r)
    print(json.dumps({"sent": ok, "debug": reasons, "token_set": bool(TOKEN), "chat_set": bool(CHAT)}))
