from core.risk import RiskConfig, position_size_for_option, hit_daily_cut

cfg = RiskConfig()
lots = position_size_for_option(balance=250000, option_price=120, lot_size=50, cfg=cfg)
print("Lots:", lots, "Total qty:", lots * 50)

print("Hit daily cut?", hit_daily_cut(balance=250000, day_pnl=-6000, cfg=cfg))
