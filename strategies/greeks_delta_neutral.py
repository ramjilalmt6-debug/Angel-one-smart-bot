"""
Strategy: Greeks Delta-Neutral (basic)
Desc: If net delta deviates beyond threshold, generate hedge signal.
"""

from typing import List, Dict, Any
from core.risk import load_risk_config, calc_lots

def _price(md: Dict[str, Any]) -> float:
    return float(md.get("price", 150.0))

def run_strategy(market_data: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
    cfg = load_risk_config()
    signals: List[Dict[str, Any]] = []

    net_delta = float(market_data.get("net_delta", 0.0))  # portfolio delta
    th = float(market_data.get("delta_threshold", 5.0))   # absolute threshold
    symbol = market_data.get("symbol", "NIFTY")

    # Positive delta → short calls / buy puts; Negative delta → short puts / buy calls (simplified)
    lots = calc_lots(price=_price(market_data), cfg=cfg)

    if abs(net_delta) >= th and lots > 0:
        if net_delta > 0:
            signals.append({
                "action": "SELL_CALL" if market_data.get("prefer_short", True) else "BUY_PUT",
                "symbol": symbol,
                "lots": lots,
                "reason": f"Delta hedge: net_delta {net_delta:.2f} > +{th}, reducing positive delta",
                "dry_run": dry_run,
            })
        else:
            signals.append({
                "action": "SELL_PUT" if market_data.get("prefer_short", True) else "BUY_CALL",
                "symbol": symbol,
                "lots": lots,
                "reason": f"Delta hedge: net_delta {net_delta:.2f} < -{th}, reducing negative delta",
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
