#!/usr/bin/env bash
# Replacement for Pi-Star's /usr/local/bin/platformDetect.sh on the
# Bubblegum-96. Upstream decodes Raspberry Pi revision codes from
# /proc/cpuinfo; here the device-tree model string is printed instead.
# The dashboard shows the single output line as "Platform".
# Part of software/bubblegum96/pistar (not Pi-Star code). UNTESTED.
set -u
model=""
if [ -r /proc/device-tree/model ]; then
	model="$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)"
fi
if [ -n "$model" ]; then
	echo "$model"
else
	echo "Bubblegum-96 (Actions S900), $(uname -m)"
fi
