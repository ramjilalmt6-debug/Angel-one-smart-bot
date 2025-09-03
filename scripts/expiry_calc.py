from __future__ import annotations
from datetime import date, datetime, timedelta

EXPIRE_MAP = {
    "NIFTY": {"weekly": 1, "monthly": 1},  # Thu
    "BANKNIFTY":  {"weekly": 2, "monthly": 2},  # Wed
    "FINNIFTY":   {"weekly": 1, "monthly": 1},  # Tue
    "MIDCPNIFTY": {"weekly": 0, "monthly": 0},  # Mon
}

def _last_weekday_of_month(y: int, m: int, wd: int) -> date:
    if m == 12: d = date(y+1,1,1) - timedelta(days=1)
    else:       d = date(y,m+1,1) - timedelta(days=1)
    while d.weekday() != wd: d -= timedelta(days=1)
    return d

def _on_or_after(start: date, wd: int) -> date:
    return start + timedelta(days=(wd - start.weekday()) % 7)

def compute_weekly_expiry(symbol: str, k: int = 0, today: date | None = None) -> date:
    wd = EXPIRE_MAP.get(symbol.upper(), EXPIRE_MAP["NIFTY"])["weekly"]
    t  = today or date.today()
    return _on_or_after(t, wd) + timedelta(weeks=k)

def compute_monthly_expiry(symbol: str, k: int = 0, ref: date | None = None) -> date:
    wd = EXPIRE_MAP.get(symbol.upper(), EXPIRE_MAP["NIFTY"])["monthly"]
    r  = ref or date.today()
    total = (r.year*12 + (r.month-1)) + k
    y, m = divmod(total, 12); m += 1
    return _last_weekday_of_month(y, m, wd)

def compute_yearly_expiry(symbol: str, k: int = 0, ref: date | None = None) -> date:
    r = ref or date.today()
    return _last_weekday_of_month(r.year + k, 12, EXPIRE_MAP.get(symbol.upper(), EXPIRE_MAP["NIFTY"])["monthly"])

def parse_hint_to_date(symbol: str, hint: str) -> date:
    s = (hint or "").strip().upper()
    if s in ("THIS-WEEKLY","THISWEEKLY","W","W+0"): return compute_weekly_expiry(symbol,0)
    if s in ("NEXT-WEEKLY","NEXTWEEKLY","NW"):      return compute_weekly_expiry(symbol,1)
    if s.startswith("W+"):  return compute_weekly_expiry(symbol,int(s[2:]))
    if s in ("THIS-MONTHLY","THISMONTHLY","M","M+0"): return compute_monthly_expiry(symbol,0)
    if s in ("NEXT-MONTHLY","NEXTMONTHLY","NM"):      return compute_monthly_expiry(symbol,1)
    if s.startswith("M+"):  return compute_monthly_expiry(symbol,int(s[2:]))
    if s in ("THIS-YEARLY","THISYEARLY","Y","Y+0"): return compute_yearly_expiry(symbol,0)
    if s in ("NEXT-YEARLY","NEXTYEARLY","NY"):     return compute_yearly_expiry(symbol,1)
    if s.startswith("Y+"):  return compute_yearly_expiry(symbol,int(s[2:]))

    import re
    m = re.match(r"^([A-Z]{3})[-/](\d{2,4})$", s)
    if m:
        MON = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,"JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}
        yr  = int(m.group(2)); yr = 2000+yr if yr<100 else yr
        mo  = MON[m.group(1)]
        return compute_monthly_expiry(symbol, 0, date(yr, mo, 1))
    m = re.match(r"^(\d{4})[-/](\d{2})$", s)
    if m: return compute_monthly_expiry(symbol, 0, date(int(m.group(1)), int(m.group(2)), 1))
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d-%b-%Y","%d-%b-%y"):
        try: return datetime.strptime(hint, fmt).date()
        except: pass
    raise ValueError(f"Unrecognized expiry hint: {hint}")
