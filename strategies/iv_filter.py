"""
Strategy: IV / IVR Filter
Desc: Acts as a gating filter. Emits 'ALLOW'/'BLOCK' meta-signal for other strategies.
"""

from typing import List, Dict, Any

def run_strategy(market_data: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []

    iv = float(market_data.get("iv", 0.0))     # e.g., 0.22 = 22%
    ivr = float(market_data.get("ivr", 0.0))   # 0..1
    iv_min = float(market_data.get("iv_min", 0.15))
    iv_max = float(market_data.get("iv_max", 0.40))
    ivr_min = float(market_data.get("ivr_min", 0.20))
    ivr_max = float(market_data.get("ivr_max", 0.80))

    ok = (iv_min <= iv <= iv_max) and (ivr_min <= ivr <= ivr_max)
    signals.append({
        "action": "ALLOW" if ok else "BLOCK",
        "symbol": market_data.get("symbol", "NIFTY"),
        "lots": 0,
        "reason": f"IV={iv:.2f}, IVR={ivr:.2f} in range [{iv_min:.2f}-{iv_max:.2f}], [{ivr_min:.2f}-{ivr_max:.2f}] = {ok}",
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
