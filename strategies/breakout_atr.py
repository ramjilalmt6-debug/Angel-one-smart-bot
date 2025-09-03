"""
Strategy: ATR Breakout
Desc: Previous high/low + k * ATR breakout with basic volume confirm.
"""

# --- compatibility shims for risk API ---
try:
    from core.risk_adapter import load_risk_config, calc_lots  # might not exist in this repo
except Exception:
    try:
        from core.risk import RiskConfig, position_size_for_option
        def load_risk_config():
            return RiskConfig()
        def calc_lots(balance, option_price, lot_size, cfg=None):
            cfg = cfg or RiskConfig()
            return int(max(0, position_size_for_option(balance=balance, option_price=option_price, lot_size=lot_size, cfg=cfg)))
    except Exception:
        # last-resort very conservative default
        def load_risk_config():
            class _C: per_trade=0.01; lots_max=1
            return _C()
        def calc_lots(balance, option_price, lot_size, cfg=None):
            try:
                exp = float(option_price)*int(lot_size)
                per = getattr(cfg,'per_trade',0.01)
                lots = int((balance*per)/max(1.0,exp))
                mx = getattr(cfg,'lots_max',1)
                return max(0, min(lots, mx))
            except Exception:
                return 0

from typing import List, Dict, Any
from core.risk_adapter import load_risk_config, calc_lots

def _price(md: Dict[str, Any]) -> float:
    return float(md.get("price", 150.0))

def run_strategy(market_data: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
    cfg = load_risk_config()
    signals: List[Dict[str, Any]] = []

    atr = float(market_data.get("atr", 0.0))
    prev_high = float(market_data.get("prev_high", 0.0))
    prev_low  = float(market_data.get("prev_low", 0.0))
    price = float(market_data.get("price", 0.0))
    vol = float(market_data.get("volume", 0.0))
    avg_vol = float(market_data.get("avg_volume", max(vol, 1.0)))

    k = float(market_data.get("atr_k", 1.0))
    vol_mult = float(market_data.get("vol_mult", 1.2))
    symbol = market_data.get("symbol", "NIFTY")

    long_trig  = (price >= prev_high + k * atr) and (vol >= vol_mult * avg_vol)
    short_trig = (price <= prev_low  - k * atr) and (vol >= vol_mult * avg_vol)

    if long_trig:
        lots = calc_lots(price=_price(market_data), cfg=cfg)
        signals.append({
            "action": "BUY",
            "symbol": symbol,
            "lots": lots,
            "reason": f"ATR Breakout UP: price {price:.2f} ≥ {prev_high + k*atr:.2f} with vol confirm",
            "dry_run": dry_run,
        })

    if short_trig:
        lots = calc_lots(price=_price(market_data), cfg=cfg)
        signals.append({
            "action": "SELL",
            "symbol": symbol,
            "lots": lots,
            "reason": f"ATR Breakout DOWN: price {price:.2f} ≤ {prev_low - k*atr:.2f} with vol confirm",
            "dry_run": dry_run,
        })

    return signals

from ._template_entry import tick

from ._template_entry import tick as _fallback_tick


def tick(api=None, live=False):
    try:
        return _fallback_tick(api=api, live=live)
    except Exception:
        pass
