from __future__ import annotations
import csv, re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
CSV  = ROOT / "data" / "instruments.csv"

@dataclass
class Contract:
    token: int
    tradingsymbol: str
    name: str
    exch_seg: str
    instrumenttype: str
    expiry: str|None
    strike: float|None
    lotsize: int|None

class TokenMap:
    def __init__(self):
        self.by_ts: Dict[str, Contract] = {}
        self.by_key: Dict[Tuple[str,str,float,str,str], Contract] = {}
        self.mtime = 0.0

    def _norm_exp(self, exp: str) -> str:
        if not exp: return ""
        s = exp.upper().replace("/", "-").strip()
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if m: return s
        m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", s)
        if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        m = re.match(r"^(\d{2})([A-Z]{3})(\d{2,4})$", s)
        if m:
            dd, mon, yy = m.groups()
            MON={"JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06","JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"}
            yyyy = f"20{yy}" if len(yy)==2 else yy
            return f"{yyyy}-{MON[mon]}-{dd}"
        return s

    def ensure_loaded(self):
        if not CSV.exists(): raise FileNotFoundError(f"{CSV} missing; run instruments_sync.py")
        mt = CSV.stat().st_mtime
        if mt == self.mtime and self.by_ts: return
        self.by_ts.clear(); self.by_key.clear()
        with CSV.open() as f:
            r = csv.DictReader(f)
            for row in r:
                try: token = int(row["token"])
                except: continue
                ts   = (row["tradingsymbol"] or "").upper().strip()
                name = (row["name"] or "").upper().strip()
                exch = (row["exch_seg"] or "NFO").upper().strip()
                inst = (row["instrumenttype"] or "").upper().strip()
                exp  = self._norm_exp(row.get("expiry",""))
                strike = float(row.get("strike") or 0) if row.get("strike") else None
                lot    = int(float(row.get("lotsize") or 0)) if row.get("lotsize") else None
                c = Contract(token, ts, name, exch, inst, exp, strike, lot)
                self.by_ts[ts]=c
                # CE/PE key
                opt=None
                if inst in ("CE","PE","CALL","PUT"):
                    opt = "CE" if inst in ("CE","CALL") else "PE"
                elif inst in ("OPTIDX","OPTSTK"):
                    if ts.endswith("CE"): opt="CE"
                    elif ts.endswith("PE"): opt="PE"
                if name and exp and strike is not None and opt in ("CE","PE"):
                    self.by_key[(name, exp, float(strike), opt, exch)] = c
        self.mtime = mt

    def get_by_ts(self, ts:str) -> Optional[Contract]:
        self.ensure_loaded(); return self.by_ts.get(ts.upper())

    def get_token(self, name:str, expiry:str, strike:float, opt:str, exch:str="NFO") -> Optional[int]:
        self.ensure_loaded()
        exp = self._norm_exp(expiry)
        nm, op, ex = name.upper(), opt.upper(), exch.upper()
        # try as-is
        k = (nm, exp, float(strike), op, ex)
        c = self.by_key.get(k)
        if c: return c.token
        # try scaled (user passed 24500 but CSV had 2450000)
        k2 = (nm, exp, float(strike)*100.0, op, ex)
        c = self.by_key.get(k2)
        if c: return c.token
        return None

TM = TokenMap()

def get_by_tradingsymbol(ts:str) -> Optional[Contract]: return TM.get_by_ts(ts)
def get_token(name:str, expiry:str, strike:float, opt:str, exch:str="NFO") -> Optional[int]: return TM.get_token(name,expiry,strike,opt,exch)
