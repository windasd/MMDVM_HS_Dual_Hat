#!/usr/bin/env bash
# Flash MMDVM_HS firmware into the STM32F103 of the mezzanine through the
# STM32 ROM boot loader on USART1 (= the MMDVM host link, /dev/ttyOWL2),
# using GPIO-A (BOOT0) and GPIO-B (NRST).
#
# UNTESTED: the board has never been built.
#
# Usage: sudo flash-mmdvm-hs.sh <firmware.bin> [tty]
#
# Firmware: juribeparada/MMDVM_HS built with configs/MMDVM_HS_Dual_Hat.h
# (14.7456 MHz TCXO, DUPLEX, STM32_USART1_HOST, SERIAL_REPEATER), or the
# release asset mmdvm_hs_dual_hat_fw.bin. The study (section 6.3) suggests a
# rebuild with a higher SERIAL_REPEATER_BAUD for the 800x480 screen.
#
# Uses the distribution's stm32flash (apt install stm32flash), not the i386
# binaries in the firmware repository. The GPIO sequence is the one the
# firmware's own Raspberry Pi scripts use ("-i 20,-21,21:-20,21": BOOT0 high,
# NRST low, NRST high; on exit BOOT0 low, NRST high) with the sysfs numbers
# of this board. Polarity on this board: GPIO-A high = BOOT0 high (U22),
# GPIO-B low = NRST low (U23, open drain), i.e. the same as on the Pi.
#
# owl-uart cannot drive RTS/DTR as plain outputs, so stm32flash's "rts"/"dtr"
# sequences cannot be used; this is why BOOT0/NRST are on GPIOs.
set -euo pipefail

fw="${1:-}"
tty="${2:-/dev/ttyOWL2}"
gpio_tool="${MMDVM_GPIO_TOOL:-/usr/local/sbin/mmdvm-gpio}"

[ -n "$fw" ] || { echo "usage: $0 <firmware.bin> [tty]" >&2; exit 2; }
[ -r "$fw" ] || { echo "error: cannot read $fw" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "error: run as root (sysfs GPIO)" >&2; exit 1; }
[ -c "$tty" ] || { echo "error: $tty is not a character device" >&2; exit 1; }
command -v stm32flash >/dev/null || { echo "error: stm32flash not installed" >&2; exit 1; }
[ -x "$gpio_tool" ] || { echo "error: $gpio_tool not found (run install.sh)" >&2; exit 1; }

boot0="$("$gpio_tool" number boot0)"
nrst="$("$gpio_tool" number nrst)"

was_active=0
if systemctl is-active --quiet mmdvmhost.service; then
	was_active=1
	systemctl stop mmdvmhost.service
fi

restore() {
	# Whatever happened: BOOT0 low, then a reset pulse so the STM32 starts
	# from flash.
	"$gpio_tool" reset-modem || true
	if [ "$was_active" -eq 1 ]; then
		systemctl start mmdvmhost.service || true
	fi
}
trap restore EXIT

# Lines exported and driven before stm32flash takes over.
"$gpio_tool" init

stm32flash -v -w "$fw" -g 0x0 -R -i "${boot0},-${nrst},${nrst}:-${boot0},${nrst}" "$tty"

echo "Firmware written."
