#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path.home() / "angel-one-smart-bot"
ENV  = ROOT / ".env"
ENV.parent.mkdir(parents=True, exist_ok=True)
ENV.touch()

# Backup once per run
bk = ENV.with_suffix(".env.bak")
try:
    shutil.copy2(ENV, bk)
except Exception:
    pass

pairs = {
    "STRATEGY": "pcr_momentum_oi",
    "TREND_SWITCH_ENABLE": "1",
    "TREND_VOTES": "2",
    "TREND_MIN_CANDLES": "20",
    # Trend source (CDS dump me NIFTY50 token=2 mila)
    "TREND_EXCHANGE": "CDS",
    "TREND_SYMBOLTOKEN": "2",
    # Safer for indices
    "TREND_INTERVAL": "FIFTEEN_MINUTE",
    "TREND_LOOKBACK_MIN": "90",
    "TREND_ADX_TREND": "20",
    "TREND_ADX_RANGE": "18",
}

lines = ENV.read_text().splitlines()
keep = []
seen = set()

for ln in lines:
    if "=" not in ln or ln.lstrip().startswith("#"):
        keep.append(ln); continue
    k = ln.split("=", 1)[0].strip()
    if k not in pairs:
        keep.append(ln)  # preserve other keys

# fixed output order for our keys (stable)
order = [
    "STRATEGY",
    "TREND_SWITCH_ENABLE", "TREND_VOTES", "TREND_MIN_CANDLES",
    "TREND_EXCHANGE", "TREND_SYMBOLTOKEN",
    "TREND_INTERVAL", "TREND_LOOKBACK_MIN",
    "TREND_ADX_TREND", "TREND_ADX_RANGE",
]
for k in order:
    keep.append(f"{k}={pairs[k]}")

ENV.write_text("\n".join(keep) + "\n")
print("ok")
