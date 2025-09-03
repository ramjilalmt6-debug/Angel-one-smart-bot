from __future__ import annotations
import math, os
from dataclasses import dataclass

@dataclass
class RiskConfig:
    per_trade_pct: float = float(os.getenv("RISK_PER_TRADE_PCT","0.5"))
    daily_max_pct: float = float(os.getenv("RISK_MAX_DAILY_PCT","2"))
    max_open_trades: int = int(os.getenv("RISK_MAX_OPEN_TRADES","3"))
    sl_pct: float = float(os.getenv("SL_PCT","25"))

def position_size_for_option(balance: float, option_price: float, lot_size: int, cfg: RiskConfig) -> int:
    risk_money = balance * (cfg.per_trade_pct/100.0)
    risk_per_lot = option_price * (cfg.sl_pct/100.0) * lot_size
    if risk_per_lot <= 0: return 0
    return max(0, math.floor(risk_money / risk_per_lot))

def hit_daily_cut(balance: float, day_pnl: float, cfg: RiskConfig) -> bool:
    return day_pnl <= - balance * (cfg.daily_max_pct/100.0)
