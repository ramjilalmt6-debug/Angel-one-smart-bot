#!/data/data/com.termux/files/usr/bin/bash
set -e
[ -z "$NORDVPN_REQUIRED_IP" ] && exit 0
CUR=$(curl -s https://api.ipify.org)
if [ "$CUR" != "$NORDVPN_REQUIRED_IP" ]; then
  echo "[IP-GUARD] Current IP $CUR != required $NORDVPN_REQUIRED_IP"
  exit 42
fi
