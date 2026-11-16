#!/usr/bin/env bash
# Restart the Meshtastic MCU when the GPS slide switch changes.
#
# UNTESTED: the board has never been built.
#
# Why (study section 3.3): the GPS module is powered through the slide switch
# AND the RAK4630's 3V3_EN. Meshtastic looks for a GPS mainly at boot, so after
# the switch is moved the firmware has to be restarted to find (or stop
# waiting for) the module. GPIO-I carries the state of the GPS supply
# (1 = powered), GPIO-G resets the RAK4630; both through /usr/local/sbin/mmdvm-gpio.
#
# The line also drops when the Meshtastic firmware itself switches the GPS off
# (power saving, or "Toggle GPS" in its menu). Restarting the MCU then would
# be wrong, and it cannot be told apart from the slide switch on this line.
# So the restart only happens on the 0 -> 1 edge (GPS powered up), after the
# level has been stable for SETTLE seconds, and not more often than once per
# HOLDOFF seconds. Whether the firmware needs the restart at all has to be
# found out on the hardware; set RESET_MESH=0 to only log.
set -euo pipefail

INTERVAL=2
SETTLE=4
HOLDOFF=120
RESET_MESH=1
[ -r /etc/default/mmdvm-gps-switch ] && . /etc/default/mmdvm-gps-switch

GPIO=/usr/local/sbin/mmdvm-gpio
state="$("$GPIO" gps-switch)"
echo "mmdvm-gps-switch: GPS supply is $state at start"
last_reset=0
while :; do
	sleep "$INTERVAL"
	now="$("$GPIO" gps-switch)" || continue
	[ "$now" = "$state" ] && continue
	sleep "$SETTLE"
	again="$("$GPIO" gps-switch)" || continue
	[ "$again" = "$now" ] || continue
	state="$now"
	echo "mmdvm-gps-switch: GPS supply is now $state"
	if [ "$state" = 1 ] && [ "$RESET_MESH" = 1 ]; then
		t="$(date +%s)"
		if [ $((t - last_reset)) -ge "$HOLDOFF" ]; then
			echo "mmdvm-gps-switch: restarting the Meshtastic MCU so that it detects the GPS"
			"$GPIO" reset-mesh
			last_reset="$t"
		else
			echo "mmdvm-gps-switch: restarted less than ${HOLDOFF}s ago, not again"
		fi
	fi
done
