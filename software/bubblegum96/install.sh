#!/usr/bin/env bash
# Copy the files of software/bubblegum96 into place on the Bubblegum-96
# (Ubuntu 24.04). Safe to run more than once.
#
# UNTESTED: written without the target; read it before running it.
#
# What it does NOT do:
#   - install packages or build anything (see README.md, mmdvm/build.sh)
#   - install the device-tree overlay (boot-chain specific, see dts/)
#   - enable or start any service, apply netplan, restart gpsd/chrony
#   - overwrite an existing /etc/MMDVM-Host.ini, /etc/MMDVM-Display.ini or
#     /etc/default/mmdvm-fan: the new version is written next to it as
#     <name>.new
#   - overwrite any other existing configuration file without first copying
#     it to <name>.bak-<timestamp>
#
# Usage: sudo ./install.sh [--dry-run]
#   FORCE=1  run on a machine that is not aarch64
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dry=0
case "${1:-}" in
--dry-run) dry=1 ;;
"") ;;
*)
	echo "usage: $0 [--dry-run]" >&2
	exit 2
	;;
esac

if [ "$(uname -m)" != aarch64 ] && [ "${FORCE:-0}" != 1 ]; then
	echo "error: this is not an aarch64 machine; set FORCE=1 to run anyway" >&2
	exit 1
fi
if [ "$dry" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
	echo "error: run as root (sudo $0), or use --dry-run" >&2
	exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"

run() {
	if [ "$dry" -eq 1 ]; then
		echo "  would run: $*"
	else
		"$@"
	fi
}

# Programs, units: replace when different (no user data in them).
install_file() {
	local mode="$1" src="$here/$2" dst="$3"
	[ -f "$src" ] || { echo "error: missing $src" >&2; exit 1; }
	if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
		echo "unchanged: $dst"
		return 0
	fi
	echo "install:   $dst"
	run install -D -m "$mode" "$src" "$dst"
}

# User-edited configuration: never touch an existing file.
install_conf_keep() {
	local mode="$1" src="$here/$2" dst="$3"
	[ -f "$src" ] || { echo "error: missing $src" >&2; exit 1; }
	if [ ! -e "$dst" ]; then
		echo "install:   $dst"
		run install -D -m "$mode" "$src" "$dst"
	elif cmp -s "$src" "$dst"; then
		echo "unchanged: $dst"
	else
		echo "kept:      $dst (new version written to $dst.new)"
		run install -D -m "$mode" "$src" "$dst.new"
	fi
}

# System configuration owned by this package: back up, then replace.
install_conf_backup() {
	local mode="$1" src="$here/$2" dst="$3"
	[ -f "$src" ] || { echo "error: missing $src" >&2; exit 1; }
	if [ -e "$dst" ]; then
		if cmp -s "$src" "$dst"; then
			echo "unchanged: $dst"
			return 0
		fi
		echo "backup:    $dst -> $dst.bak-$stamp"
		run cp -p "$dst" "$dst.bak-$stamp"
	fi
	echo "install:   $dst"
	run install -D -m "$mode" "$src" "$dst"
}

echo "== service account and data directory"
if getent passwd mmdvm >/dev/null; then
	echo "unchanged: user mmdvm"
else
	echo "create:    system user mmdvm"
	run useradd --system --user-group --no-create-home --shell /usr/sbin/nologin mmdvm
fi
# ttyOWL2 belongs to group dialout
run usermod --append --groups dialout mmdvm
run install -d -m 0755 -o mmdvm -g mmdvm /var/lib/mmdvm

echo "== GPIO helper"
install_file 0755 gpio/mmdvm-gpio.sh /usr/local/sbin/mmdvm-gpio
install_file 0644 gpio/mmdvm-gpio-init.service /etc/systemd/system/mmdvm-gpio-init.service

echo "== MMDVM"
install_conf_keep 0644 mmdvm/MMDVM.ini /etc/MMDVM-Host.ini
install_conf_keep 0644 mmdvm/MMDVM-Display.ini /etc/MMDVM-Display.ini
install_file 0644 mmdvm/mmdvmhost.service /etc/systemd/system/mmdvmhost.service
install_file 0644 mmdvm/mmdvm-display.service /etc/systemd/system/mmdvm-display.service
install_file 0755 mmdvm/flash-mmdvm-hs.sh /usr/local/sbin/flash-mmdvm-hs

echo "== fan"
install_file 0755 fan/mmdvm-fan.sh /usr/local/sbin/mmdvm-fan
install_conf_keep 0644 fan/mmdvm-fan.default /etc/default/mmdvm-fan
install_file 0644 fan/mmdvm-fan.service /etc/systemd/system/mmdvm-fan.service

echo "== battery"
install_file 0755 power/mmdvm-battery.sh /usr/local/sbin/mmdvm-battery
install_conf_keep 0644 power/mmdvm-battery.default /etc/default/mmdvm-battery
install_file 0644 power/mmdvm-battery.service /etc/systemd/system/mmdvm-battery.service

echo "== GPS"
install_file 0755 gps/mmdvm-gps-switch.sh /usr/local/sbin/mmdvm-gps-switch
install_file 0644 gps/mmdvm-gps-switch.service /etc/systemd/system/mmdvm-gps-switch.service
install_conf_backup 0644 gps/gpsd.default /etc/default/gpsd
if [ -d /etc/chrony/conf.d ]; then
	install_conf_backup 0644 gps/chrony-gps-pps.conf /etc/chrony/conf.d/mmdvm-gps-pps.conf
else
	echo "skipped:   /etc/chrony/conf.d does not exist (apt install chrony, then run again)"
fi

echo "== Meshtastic"
install_file 0755 meshtastic/provision.sh /usr/local/sbin/mmdvm-mesh-provision

echo "== network"
install_conf_backup 0644 network/10-mmdvm-lan7500.link /etc/systemd/network/10-mmdvm-lan7500.link
install_conf_backup 0600 network/60-mmdvm-lan.yaml /etc/netplan/60-mmdvm-lan.yaml

run systemctl daemon-reload

cat <<'EOF'

Done. Nothing was enabled or started. Next steps (see README.md):
  1. Edit /etc/MMDVM-Host.ini: Callsign, Id, RXFrequency, TXFrequency, ColorCode.
  2. sudo systemctl enable --now mmdvm-gpio-init mmdvm-fan
  3. sudo systemctl enable --now mosquitto mmdvmhost mmdvm-display
  4. sudo systemctl enable gpsd && sudo systemctl restart gpsd chrony
  5. sudo netplan try
  6. Optional: sudo systemctl enable --now mmdvm-battery mmdvm-gps-switch
     (set DRY_RUN=1 in /etc/default/mmdvm-battery for the first runs)
  7. Optional gateways: bash mmdvm/build-gateways.sh
EOF
