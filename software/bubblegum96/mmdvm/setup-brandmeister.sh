#!/usr/bin/env bash
# Configure MMDVM-Host + DMRGateway for a DMR-only hotspot on BrandMeister,
# the way a Pi-Star hotspot with "DMR Master: BM_..." behaves.
#
# UNTESTED on the target. Run after build.sh, build-gateways.sh and install.sh.
#
# Why DMRGateway: the current MMDVM-Host only talks to a local gateway
# ([DMR Network] GatewayAddress / GatewayPort); the direct master connection
# of the old MMDVMHost that Pi-Star uses is gone. So BrandMeister is reached
# through DMRGateway [DMR Network 1].
#
# What it changes (each file is backed up to <file>.bak-<timestamp> first):
#   /etc/MMDVM-Host.ini  [General] Callsign, Id      [Modem] RXFrequency, TXFrequency
#                        [DMR] ColorCode             [DMR Network] Enable=1
#   /etc/DMRGateway.ini  [General] Id                [Info] Callsign, frequencies, ColorCode
#                        [XLX Network] Enabled=0
#                        [DMR Network 1] Enabled=1, Address, Port, Password; the sample's
#                        reflector-emulation rewrite rules are commented out and
#                        PassAllTG / PassAllPC pass every talk group and private call on
#                        both slots, as a plain BrandMeister hotspot does.
# The other modes are already disabled in the MMDVM-Host.ini of this package.
#
# Usage:
#   sudo bash setup-brandmeister.sh --callsign BX4XXX --id 4661234 --master 4501 \
#        --rx 433000000 --tx 438000000 [--cc 1] [--password-file FILE]
#
#   --master  BrandMeister master number (the BM_<number>_... you picked in Pi-Star);
#             the address becomes <number>.master.brandmeister.network. There is no
#             master in Taiwan in the BrandMeister list of 2026-11-16; nearby ones are
#             4501 South Korea, 4602 China, 5021 Malaysia, 5151 Philippines.
#   --rx/--tx frequencies in Hz (duplex hotspot: two different frequencies).
#   Password: the "Hotspot Security" password of your BrandMeister SelfCare account.
#             Taken from --password-file, else from $BM_PASSWORD, else asked for
#             (not echoed). Empty answer = passw0rd, the BrandMeister default when
#             Hotspot Security is off. It is written to /etc/DMRGateway.ini (mode 640,
#             group mmdvm) and nowhere else.
#   ETC_DIR=<dir> uses another directory than /etc (for trying the script out).
set -euo pipefail

ETC_DIR="${ETC_DIR:-/etc}"
HOST_INI="$ETC_DIR/MMDVM-Host.ini"
GW_INI="$ETC_DIR/DMRGateway.ini"
CALL='' ; ID='' ; MASTER='' ; RX='' ; TX='' ; CC=1 ; PWFILE=''

die() { echo "setup-brandmeister: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
	case "$1" in
	--callsign) CALL="${2:-}"; shift 2 ;;
	--id) ID="${2:-}"; shift 2 ;;
	--master) MASTER="${2:-}"; shift 2 ;;
	--rx) RX="${2:-}"; shift 2 ;;
	--tx) TX="${2:-}"; shift 2 ;;
	--cc) CC="${2:-}"; shift 2 ;;
	--password-file) PWFILE="${2:-}"; shift 2 ;;
	-h | --help) sed -n '2,38p' "$0"; exit 0 ;;
	*) die "unknown option $1" ;;
	esac
done

[[ "$CALL" =~ ^[A-Za-z0-9]{3,8}$ ]] || die "--callsign is required (letters and digits)"
[[ "$ID" =~ ^[0-9]{7}([0-9]{2})?$ ]] || die "--id must be the 7-digit DMR ID (or 9 digits with a hotspot suffix)"
[[ "$MASTER" =~ ^[0-9]{4}$ ]] || die "--master must be the 4-digit BrandMeister master number"
[[ "$RX" =~ ^[0-9]{9}$ && "$TX" =~ ^[0-9]{9}$ ]] || die "--rx and --tx are frequencies in Hz, e.g. 433000000"
[[ "$CC" =~ ^[0-9]{1,2}$ ]] && [ "$CC" -le 15 ] || die "--cc is the colour code 0..15"
[ -f "$HOST_INI" ] || die "$HOST_INI not found (run install.sh first)"
[ -f "$GW_INI" ] || die "$GW_INI not found (run build-gateways.sh first)"
CALL="${CALL^^}"

if [ -n "$PWFILE" ]; then
	[ -r "$PWFILE" ] || die "cannot read $PWFILE"
	PASSWORD="$(head -n 1 "$PWFILE")"
elif [ -n "${BM_PASSWORD:-}" ]; then
	PASSWORD="$BM_PASSWORD"
elif [ -t 0 ]; then
	read -r -s -p "BrandMeister hotspot password (Enter = passw0rd): " PASSWORD
	echo
else
	PASSWORD=''
fi
[ -n "$PASSWORD" ] || PASSWORD=passw0rd
case "$PASSWORD" in *$'\n'* | *'&'* | *'\'*) die "the password contains a character this script cannot write safely (&, \\ or a line break): edit $GW_INI by hand" ;; esac

STAMP="$(date +%Y%m%d-%H%M%S)"
cp -p "$HOST_INI" "$HOST_INI.bak-$STAMP"
cp -p "$GW_INI" "$GW_INI.bak-$STAMP"

# set_key FILE SECTION KEY VALUE: replace KEY=... inside [SECTION]; fail if the key is not there.
set_key() {
	local file="$1" section="$2" key="$3" value="$4" tmp
	tmp="$(mktemp)"
	if ! awk -v s="[$section]" -v k="$key" -v v="$value" '
		/^\[/ { in_s = ($0 == s) }
		in_s && index($0, k "=") == 1 { print k "=" v; done = 1; next }
		{ print }
		END { exit done ? 0 : 3 }' "$file" >"$tmp"; then
		rm -f "$tmp"
		die "no $key= in [$section] of $file (upstream changed the file?)"
	fi
	cat "$tmp" >"$file"
	rm -f "$tmp"
}

# In [DMR Network 1]: comment the rewrite rules out, make sure PassAllTG / PassAllPC 1 and 2 are active.
plain_bm_rules() {
	local file="$1" tmp
	tmp="$(mktemp)"
	awk '
		function flush() { if (in_s && !added) { print "PassAllTG=1"; print "PassAllTG=2"; print "PassAllPC=1"; print "PassAllPC=2"; added = 1 } }
		/^\[/ { flush(); in_s = ($0 == "[DMR Network 1]") }
		in_s && /^(TGRewrite|PCRewrite|TypeRewrite|SrcRewrite|TGDynRewrite)=/ { print "# " $0; next }
		in_s && /^(# *)?PassAll(TG|PC)=/ { next }
		in_s && /^Password=/ { flush() }
		{ print }
		END { flush() }' "$file" >"$tmp"
	cat "$tmp" >"$file"
	rm -f "$tmp"
}

set_key "$HOST_INI" General Callsign "$CALL"
set_key "$HOST_INI" General Id "$ID"
set_key "$HOST_INI" Modem RXFrequency "$RX"
set_key "$HOST_INI" Modem TXFrequency "$TX"
set_key "$HOST_INI" DMR ColorCode "$CC"
set_key "$HOST_INI" "DMR Network" Enable 1

set_key "$GW_INI" General Id "$ID"
set_key "$GW_INI" Info Callsign "$CALL"
set_key "$GW_INI" Info RXFrequency "$RX"
set_key "$GW_INI" Info TXFrequency "$TX"
set_key "$GW_INI" Info ColorCode "$CC"
set_key "$GW_INI" "XLX Network" Enabled 0
set_key "$GW_INI" "DMR Network 1" Enabled 1
set_key "$GW_INI" "DMR Network 1" Address "$MASTER.master.brandmeister.network"
set_key "$GW_INI" "DMR Network 1" Port 62031
plain_bm_rules "$GW_INI"
set_key "$GW_INI" "DMR Network 1" Password "$PASSWORD"
chmod 640 "$GW_INI" 2>/dev/null || true
chgrp mmdvm "$GW_INI" 2>/dev/null || true

cat <<EOF
BrandMeister set up: $CALL / $ID on master $MASTER, RX $RX Hz, TX $TX Hz, colour code $CC.
Backups: $HOST_INI.bak-$STAMP, $GW_INI.bak-$STAMP
Next:
  sudo systemctl enable --now mosquitto dmrgateway mmdvmhost mmdvm-display
  journalctl -u dmrgateway -f      # look for the login to the master
Static talk groups are set in BrandMeister SelfCare, as with Pi-Star.
EOF
