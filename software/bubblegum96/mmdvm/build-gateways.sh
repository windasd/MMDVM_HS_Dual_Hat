#!/usr/bin/env bash
# Build and install DMRGateway and YSFGateway with gpsd support on Ubuntu 24.04
# (arm64). Run on the Bubblegum-96 as a normal user with sudo rights, after
# build.sh.
#
# UNTESTED on the target. Read from the upstream Makefiles on 2026-11-16:
#   g4klx/DMRGateway            Makefile has a commented CFLAGS / LIBS pair
#   g4klx/YSFClients/YSFGateway with -DUSE_GPSD and -lgps; this script
#                               switches to that pair.
# Both "make install" targets copy the binary to /usr/local/bin.
#
# Configuration: the upstream sample .ini is copied to /etc only when no file
# is there yet, and [GPSD] Enable is set to 1 in that fresh copy. The port
# numbers of the samples already match ../mmdvm/MMDVM.ini:
#   DMR: host 62032 <-> gateway 62031      YSF: host 3200 <-> gateway 4200
# What is left to you: Id / Callsign, which networks to enable and their
# passwords, and "[DMR Network] Enable=1" / "[System Fusion Network] Enable=1"
# in /etc/MMDVM-Host.ini. The units are installed but not enabled.
#
# Environment:
#   SRC_DIR   where to clone (default: $HOME/src/mmdvm)
#   SKIP_APT  set to 1 to skip package installation
set -euo pipefail

SRC_DIR="${SRC_DIR:-$HOME/src/mmdvm}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "${SKIP_APT:-0}" != 1 ]; then
	sudo apt-get update
	sudo apt-get install -y build-essential git libmosquitto-dev libgps-dev gpsd
fi

mkdir -p "$SRC_DIR"

fetch() {
	local url="$1" dir="$2"
	if [ -d "$dir/.git" ]; then
		git -C "$dir" pull --ff-only
	else
		git clone "$url" "$dir"
	fi
}

# Comment the plain CFLAGS / LIBS pair and uncomment the -DUSE_GPSD pair.
use_gpsd() {
	local mk="$1"
	grep -q -- '-DUSE_GPSD' "$mk" || { echo "no USE_GPSD lines in $mk: upstream changed, edit it by hand" >&2; return 1; }
	sed -i -E \
		-e '/^(CFLAGS|LIBS)[[:space:]]*=/{/USE_GPSD|-lgps/!s/^/#/}' \
		-e '/^#(CFLAGS|LIBS)[[:space:]]*=.*(USE_GPSD|-lgps)/s/^#//' "$mk"
	grep -E '^(CFLAGS|LIBS)' "$mk"
}

# set_key FILE SECTION KEY VALUE: change KEY inside [SECTION] only.
set_key() {
	local file="$1" section="$2" key="$3" value="$4" tmp
	tmp="$(mktemp)"
	awk -v s="[$section]" -v k="$key" -v v="$value" '
		/^\[/ { in_s = ($0 == s) }
		in_s && $0 ~ "^" k "=" { print k "=" v; next }
		{ print }' "$file" >"$tmp"
	sudo install -m 644 "$tmp" "$file"
	rm -f "$tmp"
}

install_ini() {
	local sample="$1" target="$2"
	if [ -e "$target" ]; then
		echo "$target exists: left alone"
		return 0
	fi
	sudo install -m 644 "$sample" "$target"
	set_key "$target" GPSD Enable 1
	echo "$target installed from the upstream sample ([GPSD] Enable=1); set Id / Callsign and the networks"
}

fetch https://github.com/g4klx/DMRGateway.git "$SRC_DIR/DMRGateway"
use_gpsd "$SRC_DIR/DMRGateway/Makefile"
make -C "$SRC_DIR/DMRGateway" -j"$(nproc)"
sudo make -C "$SRC_DIR/DMRGateway" install
install_ini "$SRC_DIR/DMRGateway/DMRGateway.ini" /etc/DMRGateway.ini

fetch https://github.com/g4klx/YSFClients.git "$SRC_DIR/YSFClients"
use_gpsd "$SRC_DIR/YSFClients/YSFGateway/Makefile"
make -C "$SRC_DIR/YSFClients/YSFGateway" -j"$(nproc)"
sudo make -C "$SRC_DIR/YSFClients/YSFGateway" install
install_ini "$SRC_DIR/YSFClients/YSFGateway/YSFGateway.ini" /etc/YSFGateway.ini

for unit in dmrgateway.service ysfgateway.service; do
	sudo install -m 644 "$HERE/$unit" "/etc/systemd/system/$unit"
done
sudo systemctl daemon-reload
echo "done. Edit /etc/DMRGateway.ini and /etc/YSFGateway.ini, then:"
echo "  sudo systemctl enable --now dmrgateway ysfgateway"
