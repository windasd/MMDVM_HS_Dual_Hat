#!/usr/bin/env bash
# Drive the mezzanine control lines on the 96Boards LS connector through the
# legacy sysfs GPIO interface (the same interface stm32flash -i uses).
#
# UNTESTED: the board has never been built.
#
# Why this exists: U22 (BOOT0), U23 (STM32 NRST) and U26 (RAK4630 reset) take
# their inputs straight from GPIO-A, -B and -G and the schematic has no pull
# resistor on those inputs. Until the host drives the lines they float, so
# "init" has to run once per boot before MMDVM-Host starts.
#
# Line offsets inside the S900 pinctrl/GPIO chip (GPIO-A = GPIOA0 = line 0 ...)
# come from the gpio-line-names table of mainline s900-bubblegum-96.dts and
# from the Bubblegum-96 hardware manual V1.1, section 5.
#
# Needs CONFIG_GPIO_SYSFS (and CONFIG_GPIO_SYSFS_LEGACY on kernels that have
# it). The sysfs number is "chip base + offset"; the base is looked up at run
# time. Override with MMDVM_GPIO_BASE=<n> if the lookup fails.
#
# Usage: mmdvm-gpio.sh init | reset-modem | reset-mesh | boot0 <0|1>
#                      | gps-switch | number <boot0|nrst|mesh-rst|gps-switch>
#                      | status
set -euo pipefail

readonly OFF_BOOT0=0      # GPIO-A, LS pin 23: high = STM32 BOOT0 high
readonly OFF_NRST=1       # GPIO-B, LS pin 24: low  = STM32 in reset
readonly OFF_MESH_RST=6   # GPIO-G, LS pin 29: low  = RAK4630 in reset
readonly OFF_GPS_SW=8     # GPIO-I, LS pin 31: high = GPS load switch enabled
readonly SYSFS=/sys/class/gpio

die() { echo "mmdvm-gpio: $*" >&2; exit 1; }

gpio_base() {
	if [ -n "${MMDVM_GPIO_BASE:-}" ]; then
		echo "$MMDVM_GPIO_BASE"
		return 0
	fi
	local chip
	for chip in "$SYSFS"/gpiochip*; do
		[ -r "$chip/device/of_node/compatible" ] || continue
		if tr '\0' '\n' <"$chip/device/of_node/compatible" | grep -qx 'actions,s900-pinctrl'; then
			cat "$chip/base"
			return 0
		fi
	done
	return 1
}

gpio_num() {
	local base
	base="$(gpio_base)" || die "S900 GPIO chip not found in $SYSFS (CONFIG_GPIO_SYSFS? set MMDVM_GPIO_BASE)"
	echo $((base + $1))
}

gpio_export() {
	local n="$1" i
	[ -d "$SYSFS/gpio$n" ] && return 0
	echo "$n" >"$SYSFS/export"
	for i in 1 2 3 4 5 6 7 8 9 10; do
		[ -w "$SYSFS/gpio$n/direction" ] && return 0
		sleep 0.1
	done
	die "gpio$n did not appear after export"
}

# gpio_out <offset> <0|1>: output with a defined level (no glitch through input)
gpio_out() {
	local n
	n="$(gpio_num "$1")"
	gpio_export "$n"
	if [ "$2" = 1 ]; then echo high >"$SYSFS/gpio$n/direction"; else echo low >"$SYSFS/gpio$n/direction"; fi
}

gpio_in() {
	local n
	n="$(gpio_num "$1")"
	gpio_export "$n"
	echo in >"$SYSFS/gpio$n/direction"
	cat "$SYSFS/gpio$n/value"
}

cmd="${1:-}"
case "$cmd" in
init)
	# BOOT0 low first, then release both resets.
	gpio_out "$OFF_BOOT0" 0
	gpio_out "$OFF_NRST" 1
	gpio_out "$OFF_MESH_RST" 1
	;;
reset-modem)
	gpio_out "$OFF_BOOT0" 0
	gpio_out "$OFF_NRST" 0
	sleep 0.1
	gpio_out "$OFF_NRST" 1
	;;
reset-mesh)
	gpio_out "$OFF_MESH_RST" 0
	sleep 0.1
	gpio_out "$OFF_MESH_RST" 1
	;;
boot0)
	case "${2:-}" in
	0 | 1) gpio_out "$OFF_BOOT0" "$2" ;;
	*) die "usage: boot0 <0|1>" ;;
	esac
	;;
gps-switch)
	# 1 = slide switch ON and the RAK4630 3V3_EN (P1.02) high, 0 = GPS unpowered
	gpio_in "$OFF_GPS_SW"
	;;
number)
	case "${2:-}" in
	boot0) gpio_num "$OFF_BOOT0" ;;
	nrst) gpio_num "$OFF_NRST" ;;
	mesh-rst) gpio_num "$OFF_MESH_RST" ;;
	gps-switch) gpio_num "$OFF_GPS_SW" ;;
	*) die "usage: number <boot0|nrst|mesh-rst|gps-switch>" ;;
	esac
	;;
status)
	base="$(gpio_base)" || die "S900 GPIO chip not found"
	echo "S900 GPIO base: $base"
	for pair in "boot0:$OFF_BOOT0" "nrst:$OFF_NRST" "mesh-rst:$OFF_MESH_RST" "gps-switch:$OFF_GPS_SW"; do
		n=$((base + ${pair#*:}))
		if [ -d "$SYSFS/gpio$n" ]; then
			echo "${pair%%:*}: gpio$n $(cat "$SYSFS/gpio$n/direction") $(cat "$SYSFS/gpio$n/value")"
		else
			echo "${pair%%:*}: gpio$n (not exported)"
		fi
	done
	;;
*)
	die "usage: $0 init|reset-modem|reset-mesh|boot0 <0|1>|gps-switch|number <name>|status"
	;;
esac
