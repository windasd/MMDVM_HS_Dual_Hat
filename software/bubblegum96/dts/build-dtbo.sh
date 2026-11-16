#!/usr/bin/env bash
# Compile mmdvm-mesh-overlay.dts to a .dtbo and, optionally, merge it into the
# Bubblegum-96 base DTB at build time.
#
# UNTESTED: written without access to dtc or to the target kernel tree.
#
# Usage:
#   KSRC=/path/to/linux ./build-dtbo.sh                 # -> mmdvm-mesh.dtbo
#   KSRC=/path/to/linux ./build-dtbo.sh base.dtb        # -> also merged.dtb
#
# KSRC must be the kernel source tree the running kernel was built from (the
# overlay includes <dt-bindings/...> headers from it).
# The base DTB must have been built with symbols:
#   make ARCH=arm64 DTC_FLAGS=-@ actions/s900-bubblegum-96.dtb
# Needs: device-tree-compiler (dtc, fdtoverlay), cpp.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/mmdvm-mesh-overlay.dts"
out_dir="${OUT_DIR:-$here}"
base_dtb="${1:-}"

: "${KSRC:?set KSRC to the kernel source tree}"
[ -d "$KSRC/include/dt-bindings" ] || [ -d "$KSRC/scripts/dtc/include-prefixes" ] || {
	echo "error: $KSRC does not look like a kernel source tree" >&2
	exit 1
}
for tool in cpp dtc; do
	command -v "$tool" >/dev/null || { echo "error: $tool not found" >&2; exit 1; }
done

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
	-I "$KSRC/include" -I "$KSRC/scripts/dtc/include-prefixes" \
	"$src" -o "$tmp"

dtc -@ -I dts -O dtb -o "$out_dir/mmdvm-mesh.dtbo" "$tmp"
echo "wrote $out_dir/mmdvm-mesh.dtbo"

if [ -n "$base_dtb" ]; then
	command -v fdtoverlay >/dev/null || { echo "error: fdtoverlay not found" >&2; exit 1; }
	fdtoverlay -i "$base_dtb" -o "$out_dir/merged.dtb" "$out_dir/mmdvm-mesh.dtbo"
	echo "wrote $out_dir/merged.dtb (install it where the boot loader loads the DTB from)"
fi
