#!/usr/bin/env bash
# Fan control for the r3.0-study mezzanine.
#
# UNTESTED: the board has never been built; the curve is a starting point.
#
# Hardware (schematic generators, host_if sheet): U36 EMC2301 (hwmon driver
# "emc2305", I2C 0x2f) switches a 5 V 30 mm fan through Q20; U37 TMP102
# (hwmon "tmp102", I2C 0x49) measures the air leaving the SoC column.
# The study text names an AMC6821; the schematic has the two parts above,
# and the EMC2301 has no temperature input and no stand-alone curve, so the
# fan depends on this service (if it stops, it leaves the fan at full speed).
#
# The emc2305 driver exposes pwm1 (0..255), fan1_input and fan1_fault and has
# no pwm1_enable, so the "fancontrol" package is not used.
#
# Curve (air temperature, degrees C):
#   below T_OFF              fan off
#   T_ON .. T_MAX            linear PWM_MIN .. PWM_MAX   (starts at T_ON,
#                            keeps running down to T_OFF: hysteresis)
#   T_MAX and above          PWM_MAX
#   charger reports Charging at least PWM_CHARGE (study 7.3: raise the fan
#                            speed while fast charging)
#   sensor unreadable        PWM_MAX
# The limits can be overridden in /etc/default/mmdvm-fan.
set -euo pipefail

T_OFF=30
T_ON=33
T_MAX=45
PWM_MIN=90
PWM_MAX=255
PWM_CHARGE=150
INTERVAL=5

# shellcheck disable=SC1091
[ -r /etc/default/mmdvm-fan ] && . /etc/default/mmdvm-fan

log() { echo "mmdvm-fan: $*"; }

# hwmon numbers change between boots: look the devices up by driver name.
find_hwmon() {
	local d
	for d in /sys/class/hwmon/hwmon*; do
		[ -r "$d/name" ] || continue
		if [ "$(cat "$d/name")" = "$1" ]; then
			echo "$d"
			return 0
		fi
	done
	return 1
}

wait_hwmon() {
	local i path
	for i in $(seq 1 30); do
		if path="$(find_hwmon "$1")"; then
			echo "$path"
			return 0
		fi
		sleep 2
	done
	return 1
}

fan="$(wait_hwmon emc2305)" || { log "no emc2305 hwmon device"; exit 1; }
[ -w "$fan/pwm1" ] || { log "$fan/pwm1 not writable"; exit 1; }

set_pwm() { echo "$1" >"$fan/pwm1"; }

# Fail safe: whatever ends this script leaves the fan at full speed.
trap 'set_pwm "$PWM_MAX" || true' EXIT
trap 'exit 0' TERM INT

set_pwm "$PWM_MAX"

if ! sensor="$(wait_hwmon tmp102)"; then
	log "no tmp102 hwmon device; fan stays at full speed"
	sensor=""
fi
log "fan: $fan sensor: ${sensor:-none}"

charging() {
	local f
	for f in /sys/class/power_supply/*bq25890*/status; do
		[ -r "$f" ] || continue
		[ "$(cat "$f")" = "Charging" ] && return 0
	done
	return 1
}

running=0
last=-1
while :; do
	pwm="$PWM_MAX"
	if [ -n "$sensor" ] && milli="$(cat "$sensor/temp1_input" 2>/dev/null)" && [[ "$milli" =~ ^-?[0-9]+$ ]]; then
		if [ "$milli" -ge $((T_MAX * 1000)) ]; then
			pwm="$PWM_MAX"
			running=1
		elif [ "$milli" -ge $((T_ON * 1000)) ] || { [ "$running" -eq 1 ] && [ "$milli" -gt $((T_OFF * 1000)) ]; }; then
			span=$(((T_MAX - T_OFF) * 1000))
			pwm=$((PWM_MIN + (PWM_MAX - PWM_MIN) * (milli - T_OFF * 1000) / span))
			running=1
		else
			pwm=0
			running=0
		fi
	fi
	if charging && [ "$pwm" -lt "$PWM_CHARGE" ]; then
		pwm="$PWM_CHARGE"
	fi
	if [ "$pwm" -ne "$last" ]; then
		set_pwm "$pwm"
		last="$pwm"
	fi
	sleep "$INTERVAL"
done
