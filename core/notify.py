from __future__ import annotations
import os, json, urllib.request, urllib.parse

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT  = os.getenv("TELEGRAM_CHAT_ID")

def tg(msg: str):
    if not (TOKEN and CHAT): return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data, method="POST"), timeout=10)
    except Exception:
        pass
