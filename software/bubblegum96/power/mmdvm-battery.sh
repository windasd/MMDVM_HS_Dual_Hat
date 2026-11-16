#!/usr/bin/env bash
# Shut the host down cleanly before the 1S4P pack is empty.
#
# UNTESTED: the board has never been built.
#
# Hardware: MAX17048 fuel gauge (I2C 0x36, mainline driver max17040_battery,
# power_supply type "Battery") and BQ25895 charger (driver bq25890_charger,
# type "USB"). The cell protector (BQ29707) cuts the pack at 2.80 V per the
# data sheet; the host should be down well before that, because the 12 V
# boost draws its highest current at the lowest cell voltage.
#
# The devices are found by power_supply type at run time, the sysfs names
# are not assumed. Limits come from /etc/default/mmdvm-battery.
#
# Shutdown happens when the pack is NOT being charged and, for COUNT
# consecutive readings, either the gauge reports SOC <= SOC_MIN or the
# voltage is <= VOLT_MIN_MV. After the host is down the STM6601 drops the
# host rails (PS_HOLD follows +1V8); the Meshtastic side stays on.
set -euo pipefail

SOC_MIN=8
VOLT_MIN_MV=3250
COUNT=3
INTERVAL=30
DRY_RUN=0
[ -r /etc/default/mmdvm-battery ] && . /etc/default/mmdvm-battery

PS=/sys/class/power_supply

find_type() {
	local want="$1" d
	for d in "$PS"/*; do
		[ -r "$d/type" ] || continue
		if [ "$(cat "$d/type")" = "$want" ]; then
			echo "$d"
			return 0
		fi
	done
	return 1
}

read_int() {
	local v
	v="$(cat "$1" 2>/dev/null)" || return 1
	case "$v" in '' | *[!0-9-]*) return 1 ;; esac
	echo "$v"
}

charging() {
	# "Charging" / "Full" from either device counts as external power present.
	local d s
	for d in "$PS"/*; do
		[ -r "$d/status" ] || continue
		s="$(cat "$d/status" 2>/dev/null || true)"
		case "$s" in Charging | Full) return 0 ;; esac
	done
	if [ -n "${CHARGER:-}" ] && [ "$(cat "$CHARGER/online" 2>/dev/null || echo 0)" = 1 ]; then
		return 0
	fi
	return 1
}

BAT="$(find_type Battery)" || { echo "mmdvm-battery: no power_supply of type Battery (max17040_battery loaded? DT overlay applied?)" >&2; exit 1; }
CHARGER="$(find_type USB || true)"
echo "mmdvm-battery: gauge $BAT, charger ${CHARGER:-none}; shutdown at SOC <= ${SOC_MIN}% or <= ${VOLT_MIN_MV} mV, $COUNT readings"

low=0
while :; do
	soc="$(read_int "$BAT/capacity" || echo -1)"
	uv="$(read_int "$BAT/voltage_now" || echo -1)"
	mv=$((uv >= 0 ? uv / 1000 : -1))
	if charging; then
		low=0
	elif { [ "$soc" -ge 0 ] && [ "$soc" -le "$SOC_MIN" ]; } || { [ "$mv" -ge 0 ] && [ "$mv" -le "$VOLT_MIN_MV" ]; }; then
		low=$((low + 1))
		echo "mmdvm-battery: low ($soc %, $mv mV), reading $low of $COUNT"
	else
		low=0
	fi
	if [ "$low" -ge "$COUNT" ]; then
		echo "mmdvm-battery: battery low ($soc %, $mv mV): shutting down"
		if [ "$DRY_RUN" = 1 ]; then
			echo "mmdvm-battery: DRY_RUN=1, not shutting down"
			low=0
		else
			exec systemctl poweroff
		fi
	fi
	sleep "$INTERVAL"
done
