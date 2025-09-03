#!/usr/bin/env python3
import os, sys, pyotp, json
from SmartApi.smartConnect import SmartConnect

ts   = sys.argv[1]        # tradingsymbol
tok  = sys.argv[2]        # symboltoken
qty  = int(sys.argv[3])   # quantity (lot multiple)
p    = float(sys.argv[4]) # limit price
trig = float(sys.argv[5]) # trigger price

api  = os.environ["SMARTAPI_API_KEY"]
cid  = os.environ["SMARTAPI_CLIENT_CODE"]
pwd  = os.environ["SMARTAPI_PASSWORD"]
totp = pyotp.TOTP(os.environ["TOTP_SECRET"]).now()

sc = SmartConnect(api)
sc.generateSession(cid, pwd, totp)

order = {
  "variety":"STOPLOSS",
  "tradingsymbol": ts,
  "symboltoken": tok,
  "transactiontype":"SELL",
  "exchange":"NFO",
  "ordertype":"STOPLOSS_LIMIT",
  "producttype":"INTRADAY",
  "duration":"DAY",
  "quantity":qty,
  "price":p,
  "triggerprice":trig
}
print(json.dumps(sc.placeOrder(order), ensure_ascii=False))
