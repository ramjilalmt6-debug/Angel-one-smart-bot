from __future__ import annotations
try:
    from core.risk import RiskConfig, position_size_for_option
except Exception as e:
    # very conservative fallbacks if risk.py shape changes
    class RiskConfig:
        def __init__(self):
            self.per_trade = 0.01
            self.lots_max = 1
    def position_size_for_option(balance: float, option_price: float, lot_size: int, cfg: RiskConfig|None=None) -> int:
        cfg = cfg or RiskConfig()
        try:
            exp = float(option_price) * int(lot_size)
            lots = int((float(balance) * float(cfg.per_trade)) / max(1.0, exp))
            return max(0, min(lots, int(getattr(cfg,'lots_max',1))))
        except Exception:
            return 0

def load_risk_config() -> RiskConfig:
    return RiskConfig()

def calc_lots(balance: float, option_price: float, lot_size: int, cfg: RiskConfig|None=None) -> int:
    cfg = cfg or RiskConfig()
    return int(max(0, position_size_for_option(balance=balance, option_price=option_price, lot_size=lot_size, cfg=cfg)))
