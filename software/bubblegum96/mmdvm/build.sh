#!/usr/bin/env bash
# Build and install MMDVM-Host and MMDVM-Display from source on Ubuntu 24.04
# (arm64). Run on the Bubblegum-96 as a normal user with sudo rights.
#
# UNTESTED on the target. Dependencies were read from the upstream Makefiles
# and sources on 2026-11-16:
#   MMDVM-Host:    C++17, -lmosquitto, <nlohmann/json.hpp>
#   MMDVM-Display: C++11, -lmosquitto
# Both "make install" targets copy the binaries to /usr/local/bin.
#
# This script does not install configuration files or systemd units; that is
# done by ../install.sh. It never touches /etc/MMDVM-Host.ini.
#
# Environment:
#   SRC_DIR   where to clone (default: $HOME/src/mmdvm)
#   SKIP_APT  set to 1 to skip package installation
set -euo pipefail

SRC_DIR="${SRC_DIR:-$HOME/src/mmdvm}"
DATA_DIR=/var/lib/mmdvm
HOST_REPO=https://github.com/g4klx/MMDVM-Host.git
DISPLAY_REPO=https://github.com/g4klx/MMDVM-Display.git

if [ "${SKIP_APT:-0}" != 1 ]; then
	sudo apt-get update
	sudo apt-get install -y build-essential git libmosquitto-dev nlohmann-json3-dev \
		mosquitto mosquitto-clients
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

fetch "$HOST_REPO" "$SRC_DIR/MMDVM-Host"
fetch "$DISPLAY_REPO" "$SRC_DIR/MMDVM-Display"

jobs="$(nproc)"
make -C "$SRC_DIR/MMDVM-Host" -j"$jobs"
make -C "$SRC_DIR/MMDVM-Display" -j"$jobs"

# "install" only; not "install-service" (that target installs the upstream
# unit and its own /etc/MMDVM-Host.ini).
sudo make -C "$SRC_DIR/MMDVM-Host" install
sudo make -C "$SRC_DIR/MMDVM-Display" install

# Lookup tables referenced by /etc/MMDVM-Host.ini. Existing files are kept.
sudo install -d -m 0755 "$DATA_DIR"
for f in DMRIds.dat NXDN.csv RSSI.dat; do
	if [ -f "$SRC_DIR/MMDVM-Host/$f" ] && [ ! -e "$DATA_DIR/$f" ]; then
		sudo install -m 0644 "$SRC_DIR/MMDVM-Host/$f" "$DATA_DIR/$f"
	fi
done

echo "MMDVM-Host:    $(git -C "$SRC_DIR/MMDVM-Host" rev-parse --short HEAD)"
echo "MMDVM-Display: $(git -C "$SRC_DIR/MMDVM-Display" rev-parse --short HEAD)"
echo "Installed to /usr/local/bin. Next: sudo ../install.sh, then edit /etc/MMDVM-Host.ini."
