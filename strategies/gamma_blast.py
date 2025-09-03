"""
Strategy: Gamma Blast
Desc: IV spike + OTM activity + sudden gamma exposure change detection.
"""

from typing import List, Dict, Any
from core.risk import load_risk_config, calc_lots

def _price(md: Dict[str, Any]) -> float:
    return float(md.get("price", 150.0))

def run_strategy(market_data: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
    cfg = load_risk_config()
    signals: List[Dict[str, Any]] = []

    iv_spike = market_data.get("iv_spike", 0.0)          # e.g., +0.12 = +12%
    otm_surge = market_data.get("otm_activity", 0.0)     # normalized activity score 0..1
    gamma_change = market_data.get("gamma_exposure_chg", 0.0)  # normalized 0..1
    th_iv = float(market_data.get("th_iv_spike", 0.08))         # default 8%
    th_otm = float(market_data.get("th_otm_activity", 0.5))
    th_gex = float(market_data.get("th_gamma_chg", 0.5))
    symbol = market_data.get("symbol", "NIFTY")

    if (iv_spike >= th_iv) and (otm_surge >= th_otm) and (gamma_change >= th_gex):
        lots = calc_lots(price=_price(market_data), cfg=cfg)
        signals.append({
            "action": "BUY",
            "symbol": symbol,
            "lots": lots,
            "reason": f"GammaBlast: IV↑{iv_spike:.2f}, OTM↑{otm_surge:.2f}, ΓΔ↑{gamma_change:.2f}",
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
