#!/usr/bin/env bash
# First-boot provisioning of the RAK4630 (Meshtastic firmware-rak4631) with
# the settings of study section 10.3, step 4.
#
# UNTESTED: the board has never been built.
#
# IMPORTANT - order of operations:
# The host link (/dev/ttySC0 = SC16IS752 channel A <-> P0.19/P0.20) only works
# AFTER the serial module has been enabled in PROTO mode on those pins. A
# freshly flashed node therefore cannot be reached on /dev/ttySC0. Run this
# script the first time over the module's USB port (J43 -> /dev/ttyACM0 on
# whatever computer it is plugged into) or over BLE, e.g.
#     ./provision.sh --port /dev/ttyACM0
#     ./provision.sh --ble "Meshtastic_1a2b"
# Later runs can use the default /dev/ttySC0.
#
# Before this script (study 10.3, steps 1-3, done with an SWD probe / USB, not
# from here): UICR REGOUT0 = 3.3 V, UICR NFCPINS = GPIO, RAK4631 boot loader,
# firmware-rak4631-*.uf2.
#
# Needs the Meshtastic Python CLI:  pipx install meshtastic
#
# Usage: provision.sh [--port TTY | --ble NAME] [--region CODE]
#                     [--sh1106] [--gps-always-on] [--dry-run]
set -euo pipefail

target=(--port /dev/ttySC0)
region=TW
sh1106=0
gps_always_on=0
dry_run=0

while [ $# -gt 0 ]; do
	case "$1" in
	--port)
		[ $# -ge 2 ] || { echo "--port needs a value" >&2; exit 2; }
		target=(--port "$2")
		shift 2
		;;
	--ble)
		[ $# -ge 2 ] || { echo "--ble needs a value" >&2; exit 2; }
		target=(--ble "$2")
		shift 2
		;;
	--region)
		[ $# -ge 2 ] || { echo "--region needs a value" >&2; exit 2; }
		region="$2"
		shift 2
		;;
	--sh1106) sh1106=1; shift ;;
	--gps-always-on) gps_always_on=1; shift ;;
	--dry-run) dry_run=1; shift ;;
	-h | --help)
		sed -n '2,24p' "$0"
		exit 0
		;;
	*)
		echo "unknown option: $1" >&2
		exit 2
		;;
	esac
done

command -v meshtastic >/dev/null || [ "$dry_run" -eq 1 ] || {
	echo "error: meshtastic CLI not found (pipx install meshtastic)" >&2
	exit 1
}

# Study 10.3 step 4:
#   LoRa region TW (920-925 MHz)
#   Serial module: enabled, PROTO, rxd 19, txd 20 (nRF52840 P0.19 / P0.20,
#   RAK4630 pads 9 / 10), 115200
#   Position: GPS as required -> gps_mode ENABLED
settings=(
	--set lora.region "$region"
	--set serial.enabled true
	--set serial.mode PROTO
	--set serial.rxd 19
	--set serial.txd 20
	--set serial.baud BAUD_115200
	--set position.gps_mode ENABLED
)

# Study 10.4: a few SH1106 panels are detected as SSD1306 on a cold start.
if [ "$sh1106" -eq 1 ]; then
	settings+=(--set display.oled OLED_SH1106)
fi

# Study 3.3: gpsd on the host only sees NMEA while the receiver is running,
# so the receiver should not be put to sleep between fixes.
# TODO(verify on hardware): that a short gps_update_interval keeps the
# receiver powered continuously with the firmware version in use. This option
# is a guess at the right knob, not a confirmed recipe.
if [ "$gps_always_on" -eq 1 ]; then
	settings+=(--set position.gps_update_interval 5)
fi

echo "Target:   ${target[*]}"
echo "Settings: ${settings[*]}"
if [ "$dry_run" -eq 1 ]; then
	exit 0
fi

# One invocation: the CLI sends all values in one transaction; the node
# reboots once afterwards.
meshtastic "${target[@]}" "${settings[@]}"

cat <<'EOF'

The node reboots now. After about 20 s check the host link:
    meshtastic --port /dev/ttySC0 --info
EOF
