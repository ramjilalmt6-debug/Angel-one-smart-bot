#!/usr/bin/env python3
import os, json, time, hashlib, importlib.util
from pathlib import Path

ROOT = Path.home() / "angel-one-smart-bot"
DATA = ROOT / "data"
LOG  = DATA / "autopilot.out"
OFF  = DATA / "alert.offset"
COOLDOWN_FILE = DATA / "alert.cooldown.json"

# --- Load .env (works even without python-dotenv) ---
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env", override=True)
except Exception:
    envp = ROOT / ".env"
    if envp.exists():
        for ln in envp.read_text().splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# --- Telegram notify bridge (scripts/notify.py -> send) ---
def send(msg: str) -> bool:
    try:
        spec = importlib.util.spec_from_file_location("notify", str(ROOT / "scripts" / "notify.py"))
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(mod)  # type: ignore
        return bool(mod.send(msg))
    except Exception:
        return False

WATCH_EVENTS = {
    "login_fail",
    "trend_switched",
    "health_sentinel_alert",
    "risk_guard_trip",
    "guardian_crash",
}

def load_offset() -> int:
    try:
        return int(OFF.read_text().strip())
    except Exception:
        return 0

def save_offset(n: int):
    try:
        OFF.write_text(str(n))
    except Exception:
        pass

def _load_cooldowns():
    try:
        return json.loads(COOLDOWN_FILE.read_text())
    except Exception:
        return {}

def _save_cooldowns(d):
    try:
        COOLDOWN_FILE.write_text(json.dumps(d))
    except Exception:
        pass

# --- Tunables from .env ---
COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "120"))
STARTUP_PING = os.getenv("ALERT_STARTUP_PING", "0") == "1"
START_FROM_EOF = os.getenv("ALERT_START_FROM_EOF", "0") == "1"
MAX_SEND_PER_RUN = int(os.getenv("ALERT_MAX_SEND_PER_RUN", "0"))  # 0 = unlimited

def main() -> int:
    if not LOG.exists():
        print(json.dumps({"event": "alert_watch_note", "msg": "log_missing"}))
        return 0

    if STARTUP_PING:
        send("🚀 alert_watch up")

    # handle rotation + optional EOF start
    offset = load_offset()
    sz = LOG.stat().st_size
    if offset > sz:
        offset = 0
    if offset == 0 and START_FROM_EOF:
        offset = sz

    with LOG.open("rb") as f:
        f.seek(offset)
        new_data = f.read()
        new_off = f.tell()

    sent = 0
    for raw in new_data.splitlines():
        try:
            line = raw.decode("utf-8", "replace").strip()
            if not line or not line.startswith("{"):
                continue
            J = json.loads(line)
            ev = str(J.get("event") or "")
        except Exception:
            continue

        if ev in WATCH_EVENTS:
            # Per-message cooldown key
            def _ckey() -> str:
                if ev == "login_fail":
                    base = f"{ev}:{J.get('err','')}"
                elif ev == "trend_switched":
                    base = f"{ev}:{J.get('from')}->{J.get('to')}"
                else:
                    base = f"{ev}:{line}"
                h = hashlib.md5(base.encode("utf-8", "ignore")).hexdigest()  # nosec: fingerprint only
                return f"{ev}:{h}"

            _cool = _load_cooldowns()
            key = _ckey()
            now = int(time.time())
            last = int(_cool.get(key, 0))
            if now - last < COOLDOWN_SEC:
                continue

            # Craft message
            if ev == "login_fail":
                msg = f"⚠️ Login FAIL: {J.get('err','')[:180]}"
            elif ev == "trend_switched":
                msg = f"🔀 Switched {J.get('from')} → {J.get('to')} (ADX {J.get('adx')}, {J.get('status')})"
            elif ev == "health_sentinel_alert":
                issues = ", ".join(J.get("issues", []))[:300]
                msg = f"🚑 Health issue: {issues}"
            elif ev == "risk_guard_trip":
                msg = "🛑 Risk Guard tripped. Positions square-off attempted."
            else:
                msg = f"ℹ️ {ev}"

            if send(msg):
                sent += 1
                _cool[key] = now
                _save_cooldowns(_cool)
                if MAX_SEND_PER_RUN and sent >= MAX_SEND_PER_RUN:
                    break

    save_offset(new_off)
    print(json.dumps({
        "event": "alert_watch_ok",
        "processed_bytes": len(new_data),
        "sent": sent,
        "cooldown_sec": COOLDOWN_SEC
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
