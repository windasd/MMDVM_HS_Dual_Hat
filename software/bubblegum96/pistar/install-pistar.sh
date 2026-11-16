#!/usr/bin/env bash
# Assemble a Pi-Star system on a Bubblegum-96 (Ubuntu 24.04 arm64) carrying
# the r3.0-study mezzanine (MMDVM_HS dual hat on /dev/ttyOWL2).
#
# UNTESTED. This script has never been run: there is no Bubblegum-96 with
# the board and no Ubuntu arm64 machine where it was written. It passes
# "bash -n" and its text-processing steps (sed edits, patch, sudoers
# extraction) were exercised on a PC against the pinned upstream commits.
# Read README.md ("UNTESTED") before running it, and run --dry-run first.
#
# Nothing of Pi-Star is contained in this repository (the Pi-Star
# repositories carry no licence). This script downloads the dashboard, the
# management scripts and Pi-Star's default configuration from upstream at
# the commits pinned in pins.conf, edits them in place on the target
# (every edit is listed with its reason in the adapt_* functions and in
# patches/), and builds the radio programs from the g4klx sources at the
# commits the Pi-Star 4.3 binaries were built from.
#
# Usage: sudo bash install-pistar.sh [options]
#   --dry-run          print every action, change nothing (no root needed)
#   --skip-apt         do not install packages
#   --skip-build       do not build the radio programs
#   --no-gpsd          build the gateways without gpsd support
#   --with-dstar       also build ircDDBGateway (wxWidgets; see FEATURES.md)
#   --with-firewall    run Pi-Star's iptables script at every boot
#   --hostname NAME    set the system host name (Pi-Star's default: pi-star)
# Environment:
#   FORCE=1            run on a machine that is not aarch64
#
# The script is idempotent: files are replaced only when it installed them
# itself (see /var/lib/pistar-b96/manifest), configuration that already
# exists is kept, foreign files in the way are moved to
# /var/lib/pistar-b96/displaced and put back by uninstall-pistar.sh.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pins.conf
. "$here/pins.conf"

DRY=0
SKIP_APT=0
SKIP_BUILD=0
WITH_GPSD=1
WITH_DSTAR=0
WITH_FIREWALL=0
NEW_HOSTNAME=""

STATE=/var/lib/pistar-b96
MANIFEST="$STATE/manifest"           # programs, units, web files
MANIFEST_CONF="$STATE/manifest-conf" # configuration created here (kept by a plain uninstall)
DISPLACED="$STATE/displaced"
SRC=/opt/pistar-b96/src
DASH=/var/www/dashboard
UNIT_DIR=/lib/systemd/system
LOGDIR=/var/log/pi-star
ETC_SHARE=/usr/local/etc
PRESETS=/usr/local/sbin/pistar-b96-presets
MODEM_TTY=ttyOWL2
WIFI_IF=wlan0
STAMP="$(date +%Y%m%d-%H%M%S)"

# Pi-Star's well-known initial web login (user pi-star). It is used only
# when no password is typed at the prompt; the dashboard then shows a
# warning banner and forces a change for clients outside the local subnet
# (config/banner_warnings.inc). Never echoed.
PISTAR_WEB_USER=pi-star
PISTAR_DEFAULT_WEB_PASSWORD=raspberry

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() {
	printf 'install-pistar: error: %s\n' "$*" >&2
	exit 1
}

have() { command -v "$1" >/dev/null 2>&1; }

# run <command...>: execute, or print in --dry-run.
run() {
	if [ "$DRY" -eq 1 ]; then
		printf '  would run:'
		printf ' %q' "$@"
		printf '\n'
	else
		"$@"
	fi
}

# record <path> [manifest]: remember that this script created <path>.
record() {
	local m="${2:-$MANIFEST}"
	if [ "$DRY" -eq 1 ]; then return 0; fi
	if ! grep -qxF -- "$1" "$m" 2>/dev/null; then
		printf '%s\n' "$1" >>"$m"
	fi
}

owned() {
	grep -qxF -- "$1" "$MANIFEST" 2>/dev/null && return 0
	grep -qxF -- "$1" "$MANIFEST_CONF" 2>/dev/null && return 0
	return 1
}

# displace <path>: move a file this script did not create out of the way.
displace() {
	local p="$1" dst
	if [ ! -e "$p" ] && [ ! -L "$p" ]; then return 0; fi
	if owned "$p"; then return 0; fi
	dst="$DISPLACED$p"
	if [ -e "$dst" ] || [ -L "$dst" ]; then dst="$dst.$STAMP"; fi
	say "displace:  $p -> $dst (uninstall-pistar.sh puts it back)"
	run install -d -m 0755 "$(dirname "$dst")"
	run mv -- "$p" "$dst"
}

# put <src> <dst> <mode> [owner:group]: install a program / unit / web file.
put() {
	local src="$1" dst="$2" mode="$3" og="${4:-root:root}"
	if [ "$DRY" -eq 0 ] && [ ! -f "$src" ]; then die "missing source file $src"; fi
	displace "$dst"
	say "install:   $dst"
	run install -D -m "$mode" -o "${og%%:*}" -g "${og##*:}" "$src" "$dst"
	record "$dst"
}

# put_conf <src> <dst> <mode> [owner:group]: configuration, never overwritten.
# Returns 0 when the file was created, 1 when an existing file was kept.
put_conf() {
	local src="$1" dst="$2" mode="$3" og="${4:-root:root}"
	if [ -e "$dst" ]; then
		say "kept:      $dst"
		return 1
	fi
	if [ "$DRY" -eq 0 ] && [ ! -f "$src" ]; then die "missing source file $src"; fi
	say "install:   $dst"
	run install -D -m "$mode" -o "${og%%:*}" -g "${og##*:}" "$src" "$dst"
	record "$dst" "$MANIFEST_CONF"
	return 0
}

# write_file <dst> <mode> [owner:group]: content on stdin, replaced on re-run.
write_file() {
	local dst="$1" mode="$2" og="${3:-root:root}" tmp
	if [ "$DRY" -eq 1 ]; then
		cat >/dev/null
		displace "$dst"
		say "  would write: $dst (mode $mode, $og)"
		return 0
	fi
	tmp="$(mktemp)"
	cat >"$tmp"
	put "$tmp" "$dst" "$mode" "$og"
	rm -f "$tmp"
}

# write_conf <dst> <mode> [owner:group]: content on stdin, kept if it exists.
write_conf() {
	local dst="$1" mode="$2" og="${3:-root:root}" tmp
	if [ -e "$dst" ]; then
		cat >/dev/null
		say "kept:      $dst"
		return 0
	fi
	if [ "$DRY" -eq 1 ]; then
		cat >/dev/null
		say "  would write: $dst (mode $mode, $og)"
		return 0
	fi
	tmp="$(mktemp)"
	cat >"$tmp"
	put_conf "$tmp" "$dst" "$mode" "$og" || true
	rm -f "$tmp"
}

# clone_pinned <url> <dir> <commit>: clone (or reuse) and force the work tree
# to exactly <commit>; stop if that cannot be verified.
clone_pinned() {
	local url="$1" dir="$2" commit="$3" head
	say "fetch:     $url @ $commit"
	say "           -> $dir"
	if [ "$DRY" -eq 1 ]; then
		say "  would run: git clone --no-checkout (or fetch), checkout --detach $commit,"
		say "             reset --hard, clean -fdx, verify HEAD == pin and a clean tree"
		return 0
	fi
	if [ ! -d "$dir/.git" ]; then
		if [ -e "$dir" ] && [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
			die "$dir exists and is not a git checkout; move it away first"
		fi
		install -d -m 0755 "$(dirname "$dir")"
		git clone --quiet --no-checkout "$url" "$dir"
	fi
	if ! git -C "$dir" cat-file -e "${commit}^{commit}" 2>/dev/null; then
		git -C "$dir" fetch --quiet origin
	fi
	git -C "$dir" cat-file -e "${commit}^{commit}" 2>/dev/null ||
		die "commit $commit does not exist in $url"
	git -C "$dir" -c advice.detachedHead=false checkout --quiet --force --detach "$commit"
	git -C "$dir" reset --quiet --hard "$commit"
	git -C "$dir" clean --quiet -fdx
	head="$(git -C "$dir" rev-parse HEAD)"
	[ "$head" = "$commit" ] || die "$dir is at $head, expected $commit"
	[ -z "$(git -C "$dir" status --porcelain)" ] || die "$dir is not clean after checkout"
}

# apply_patches <git work tree> <patch directory>: stop if one does not apply.
apply_patches() {
	local tree="$1" pdir="$2" p
	[ -d "$pdir" ] || return 0
	for p in "$pdir"/*.patch; do
		[ -f "$p" ] || continue
		say "patch:     $(basename "$p") -> $tree"
		if [ "$DRY" -eq 1 ]; then
			say "  would run: git -C $tree apply --check, then apply"
			continue
		fi
		git -C "$tree" apply --check "$p" ||
			die "patch $(basename "$p") does not apply to $tree (pin changed?)"
		git -C "$tree" apply "$p"
	done
}

# sed_expect <file> <count> <fixed string> <sed expression>
# Edit a pinned upstream file. The fixed string must occur on exactly <count>
# lines before the edit and on none afterwards, otherwise upstream is not
# what this script was written against and the installation stops.
sed_expect() {
	local file="$1" want="$2" fixed="$3" expr="$4" got
	say "edit:      $file ($want x '$fixed')"
	if [ "$DRY" -eq 1 ]; then
		say "  would run: sed -i $expr"
		return 0
	fi
	[ -f "$file" ] || die "$file does not exist (upstream layout changed?)"
	got="$(grep -cF -- "$fixed" "$file" || true)"
	[ "$got" = "$want" ] || die "$file: expected $want line(s) with '$fixed', found $got"
	sed -i "$expr" "$file"
	if grep -qF -- "$fixed" "$file"; then
		die "$file: '$fixed' still present after the edit"
	fi
}

# neutralise_remount_ro <tree> <find args...>
# Pi-Star keeps its root file system read-only and remounts it around every
# write. Ubuntu here runs from a read-write root; "mount -o remount,ro /"
# must never run (it normally fails as busy, and if it ever succeeded the
# system would be crippled until reboot; for /boot it would succeed).
# Every "[sudo ]mount -o remount,ro" becomes "true" (the mount point that
# follows turns into an ignored argument of true); "remount,rw" is left
# alone because it is harmless.
neutralise_remount_ro() {
	local tree="$1"
	shift
	say "edit:      $tree: every '[sudo ]mount -o remount,ro' -> 'true'"
	if [ "$DRY" -eq 1 ]; then
		say "  would run: sed -i -E 's#(sudo )?mount -o remount,ro#true#g' on the matching files"
		return 0
	fi
	local f n=0
	while IFS= read -r -d '' f; do
		if grep -q 'mount -o remount,ro' "$f"; then
			sed -i -E 's#(sudo )?mount -o remount,ro#true#g' "$f"
			n=$((n + 1))
		fi
	done < <(find "$tree" -path "$tree/.git" -prune -o -type f "$@" -print0)
	[ "$n" -gt 0 ] || die "$tree: no 'mount -o remount,ro' found (upstream changed?)"
	if grep -rq --exclude-dir=.git 'mount -o remount,ro' "$tree"; then
		die "$tree: 'mount -o remount,ro' still present after the edit"
	fi
	say "           $n file(s) edited"
}

# ---------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------

parse_args() {
	while [ "$#" -gt 0 ]; do
		case "$1" in
		--dry-run) DRY=1 ;;
		--skip-apt) SKIP_APT=1 ;;
		--skip-build) SKIP_BUILD=1 ;;
		--no-gpsd) WITH_GPSD=0 ;;
		--with-dstar) WITH_DSTAR=1 ;;
		--with-firewall) WITH_FIREWALL=1 ;;
		--hostname)
			shift
			NEW_HOSTNAME="${1:-}"
			[[ "$NEW_HOSTNAME" =~ ^[a-z0-9]([a-z0-9-]{0,13}[a-z0-9])?$ ]] ||
				die "--hostname needs a name of 1-15 characters a-z 0-9 -"
			;;
		-h | --help)
			sed -n '2,36p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
			exit 0
			;;
		*) die "unknown option $1 (see --help)" ;;
		esac
		shift
	done
}

preflight() {
	step "preflight"
	if [ "$(uname -m)" != aarch64 ] && [ "${FORCE:-0}" != 1 ] && [ "$DRY" -eq 0 ]; then
		die "this is not an aarch64 machine; set FORCE=1 to run anyway"
	fi
	if [ "$DRY" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
		die "run as root (sudo bash $0), or use --dry-run"
	fi
	if [ -r /etc/os-release ]; then
		# shellcheck disable=SC1091
		if ! (. /etc/os-release && [ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = 24.04 ]); then
			warn "this is not Ubuntu 24.04; package names and paths below assume it"
		fi
	fi
	if [ "$DRY" -eq 0 ]; then
		install -d -m 0755 "$STATE" "$DISPLACED"
		touch "$MANIFEST" "$MANIFEST_CONF"
	fi
	check_minimal_package
	local f
	for f in /usr/local/sbin/mmdvm-gpio /usr/local/sbin/flash-mmdvm-hs; do
		if [ ! -x "$f" ]; then
			warn "$f is missing. The board files of ../install.sh (GPIO helper, flash script,"
			warn "gpsd, fan, battery, network) are needed by both packages; run it as well."
		fi
	done
	if [ ! -c "/dev/$MODEM_TTY" ]; then
		warn "/dev/$MODEM_TTY does not exist (device-tree overlay not applied?)"
	fi
}

# The minimal package (../mmdvm: current MQTT MMDVM-Host) and this one are
# alternatives: both use /dev/ttyOWL2 and both define mmdvmhost.service,
# dmrgateway.service and ysfgateway.service. Refuse while the other one is
# switched on; if it is installed but off, its three unit files (which would
# shadow Pi-Star's in /lib/systemd/system) are moved aside later.
check_minimal_package() {
	local u f bad=""
	have systemctl || return 0
	for u in mmdvmhost.service mmdvm-display.service dmrgateway.service ysfgateway.service; do
		f="/etc/systemd/system/$u"
		[ -f "$f" ] || continue
		if systemctl is-enabled --quiet "$u" 2>/dev/null || systemctl is-active --quiet "$u" 2>/dev/null; then
			bad="$bad $u"
		fi
	done
	if [ -n "$bad" ]; then
		cat >&2 <<EOF

install-pistar: the minimal package (software/bubblegum96/mmdvm) is switched on:
   $bad
It and Pi-Star are alternatives - both drive the modem on /dev/$MODEM_TTY and
both own the unit names mmdvmhost / dmrgateway / ysfgateway. Choose one.
To switch to Pi-Star:

    sudo systemctl disable --now mmdvmhost mmdvm-display dmrgateway ysfgateway

and run this installer again. (mmdvm-gpio-init, mmdvm-fan, mmdvm-battery,
gpsd and the network files of ../install.sh stay as they are; Pi-Star here
uses them.) Nothing was changed.
EOF
		exit 1
	fi
}

apt_packages() {
	step "packages"
	if [ "$SKIP_APT" -eq 1 ]; then
		say "skipped (--skip-apt)"
		return 0
	fi
	# Web: Pi-Star serves the dashboard with nginx + php-fpm; basic-auth
	# passwords are managed with htpasswd (apache2-utils).
	# Dashboard helpers: zip/unzip (backup), psmisc (killall, fuser),
	# netcat + util-linux "script" (calibration page), net-tools and
	# wireless-tools (ifconfig / iwconfig on the Wi-Fi page), miniupnpc
	# (only used if uPnP is switched on in the dashboard), iptables
	# (pistar-firewall, only with --with-firewall).
	local pkgs=(
		nginx php-fpm php-cli php-mbstring php-zip apache2-utils sudo
		git ca-certificates curl build-essential
		zip unzip psmisc procps netcat-openbsd cron logrotate tzdata iproute2
		net-tools wireless-tools iw wpasupplicant miniupnpc iptables
		stm32flash
	)
	if [ "$WITH_GPSD" -eq 1 ]; then pkgs+=(gpsd libgps-dev); fi
	if [ "$WITH_DSTAR" -eq 1 ]; then pkgs+=(libwxgtk3.2-dev); fi
	run apt-get update
	run env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${pkgs[@]}"
}

users_and_dirs() {
	step "users, groups, directories"
	# mmdvm: MMDVMHost and the gateways drop to this user when Daemon=1
	# (getpwnam("mmdvm") in the sources); its primary group must be able to
	# write the log directory and open the modem tty (see adapt_modem_port).
	if getent passwd mmdvm >/dev/null 2>&1; then
		say "unchanged: user mmdvm"
	else
		say "create:    system user mmdvm"
		run useradd --system --user-group --no-create-home --shell /usr/sbin/nologin mmdvm
		if [ "$DRY" -eq 0 ]; then touch "$STATE/created-user-mmdvm"; fi
	fi
	# pi-star: the dashboard's "change password" runs chpasswd for this
	# Linux user as well as htpasswd. It exists only for that: no password
	# until the dashboard sets one, and no login shell at any time.
	if getent passwd "$PISTAR_WEB_USER" >/dev/null 2>&1; then
		say "unchanged: user $PISTAR_WEB_USER"
	else
		say "create:    user $PISTAR_WEB_USER (no login shell, password locked)"
		run useradd --no-create-home --shell /usr/sbin/nologin "$PISTAR_WEB_USER"
		if [ "$DRY" -eq 0 ]; then touch "$STATE/created-user-pi-star"; fi
	fi
	# Log directory exactly as the Pi-Star service wrappers create it.
	run install -d -m 0775 -o root -g mmdvm "$LOGDIR"
	run install -d -m 0755 "$ETC_SHARE" "$SRC" /usr/local/bin/firmware
	record "$LOGDIR/"
	record "/usr/local/bin/firmware/"
	record "/opt/pistar-b96/"
}

fetch_pistar() {
	step "Pi-Star dashboard, scripts, default configuration (from upstream)"
	local keep="" f
	# The dashboard rewrites three tracked files at run time (callsign, log
	# paths, time zone, language). Carry them over a re-installation.
	if [ "$DRY" -eq 0 ] && [ -d "$DASH/.git" ]; then
		keep="$(mktemp -d)"
		for f in config.php language.php ircddblocal.php; do
			if [ -f "$DASH/config/$f" ]; then cp -p "$DASH/config/$f" "$keep/$f"; fi
		done
	fi
	if [ "$DRY" -eq 0 ] && [ -e "$DASH" ] && [ ! -d "$DASH/.git" ]; then
		displace "$DASH"
	fi
	clone_pinned "$URL_DASH" "$DASH" "$PIN_DASH"
	record "$DASH/"
	adapt_dashboard
	if [ -n "$keep" ]; then
		for f in config.php language.php ircddblocal.php; do
			if [ -f "$keep/$f" ]; then
				say "kept:      $DASH/config/$f (run-time settings of the dashboard)"
				install -m 0644 -o root -g root "$keep/$f" "$DASH/config/$f"
			fi
		done
		rm -rf "$keep"
	fi
	clone_pinned "$URL_SBIN" "$SRC/sbin" "$PIN_SBIN"
	clone_pinned "$URL_BIN" "$SRC/bin" "$PIN_BIN"
}

# Edits to the pinned dashboard. Unified diffs live in patches/dashboard/.
adapt_dashboard() {
	# 1. Read-only root handling (see neutralise_remount_ro).
	neutralise_remount_ro "$DASH" '(' -name '*.php' -o -name '*.inc' ')'

	# 2. CPU temperature. Pi-Star reads thermal_zone0, which exists only if
	#    the kernel has a thermal driver for the S900 (mainline had none
	#    when this was written). board/pistar-b96-temp prints the same
	#    format from thermal_zone0 or, failing that, from the mezzanine's
	#    TMP102 (outlet air, not the SoC).
	sed_expect "$DASH/admin/configure.php" 1 'cat /sys/class/thermal/thermal_zone0/temp' \
		's#cat /sys/class/thermal/thermal_zone0/temp#/usr/local/sbin/pistar-b96-temp#'
	sed_expect "$DASH/dstarrepeater/system.php" 1 'cat /sys/class/thermal/thermal_zone0/temp' \
		's#cat /sys/class/thermal/thermal_zone0/temp#/usr/local/sbin/pistar-b96-temp#'

	# 3. "Reset WiFi Adapter" calls ifdown / ifup (ifupdown), which Ubuntu
	#    24.04 does not have. Use the "ip link" form the same page already
	#    uses after saving; it is in Pi-Star's sudoers allowlist.
	sed_expect "$DASH/admin/wifi.php" 1 "sudo ifdown $WIFI_IF && sleep 3 && sudo ifup $WIFI_IF" \
		"s#sudo ifdown $WIFI_IF \\&\\& sleep 3 \\&\\& sudo ifup $WIFI_IF#sudo ip link set $WIFI_IF down \\&\\& sleep 3 \\&\\& sudo ip link set $WIFI_IF up#"

	# 4. Changes that need more than one line.
	apply_patches "$DASH" "$here/patches/dashboard"
}

install_scripts() {
	step "management scripts -> /usr/local/sbin, /usr/local/bin"
	neutralise_remount_ro "$SRC/sbin"
	apply_patches "$SRC/sbin" "$here/patches/sbin"

	local s
	# Upstream scripts used as they are (after the edit above).
	local upstream=(
		HostFilesUpdate.sh pistar-firewall pistar-bmapi pistar-tgifapi pistar-dapnetapi
		pistar-link pistar-ysflink pistar-p25link pistar-nxdnlink pistar-mmdvmremote
		pistar-mmdvmcal pistar-calibration-start pistar-jittertest pistar-mmdvmhost-module
		pistar-upnp.service
		mmdvmhost.service dmrgateway.service ysfgateway.service ysfparrot.service
		dgidgateway.service p25gateway.service p25parrot.service nxdngateway.service
		nxdnparrot.service m17gateway.service dapnetgateway.service aprsgateway.service
		ysf2dmr.service ysf2nxdn.service ysf2p25.service dmr2ysf.service dmr2nxdn.service
		nxdn2dmr.service nextiondriver.service
	)
	if [ "$WITH_DSTAR" -eq 1 ]; then upstream+=(ircddbgateway.service timeserver.service); fi
	for s in "${upstream[@]}"; do
		put "$SRC/sbin/$s" "/usr/local/sbin/$s" 0755
	done

	# Not installed, with the reason (see FEATURES.md):
	#   pistar-update pistar-upgrade pistar-factory-reset pistar-watchdog
	#   pistar-modemupgrade pistar-mmdvmhshatreset pistar-findmodem
	#                              replaced by the files in board/ below
	#   pistar-daily.cron pistar-hourly.cron
	#                              replaced by board/pistar-b96-daily
	#   pistar-remote pistar-keeper (+ .service)   Python 2 programs
	#   pistar-nextiontext.py      writes to /dev/ttyAMA0 as if a display were
	#                              there; here that is the modem
	#   pistar-oledtext.py         no OLED on this board
	#   pistar-ap.service          hostapd auto-AP built on ifupdown / wlan0_ap
	#   pistar-expand pistar-clone pistar-bootconfig.sh pistar-motdgen
	#   pistar-sslgenerate pistar-sendcw mobilegps.service timercontrol.service
	#   mmdvmhost_NoOLED.service dstarrepeater.service
	#                              Raspberry Pi image management, or programs
	#                              that are not built here

	# Board replacements (this repository's own code).
	for s in pistar-update pistar-upgrade pistar-factory-reset pistar-watchdog \
		pistar-modemupgrade pistar-mmdvmhshatreset pistar-findmodem \
		pistar-b96-presets pistar-b96-temp pistar-b96-daily rpi-rw rpi-ro; do
		put "$here/board/$s" "/usr/local/sbin/$s" 0755
	done
	put "$here/board/platformDetect.sh" /usr/local/bin/platformDetect.sh 0755

	# Data from Pi-Star_v43_Binaries_Bin (its armhf programs are not used).
	put "$SRC/bin/config_clean.zip" /usr/local/bin/config_clean.zip 0644
	for s in hs_dual_hat.bin md5sum.txt version.txt; do
		put "$SRC/bin/firmware/$s" "/usr/local/bin/firmware/$s" 0644
	done
	put "$here/pins.conf" "$ETC_SHARE/pistar-b96-pins" 0644
}

# --- radio programs ----------------------------------------------------------

need_build() { # <name> <key>
	if [ "$DRY" -eq 1 ]; then return 0; fi
	if [ -f "$STATE/built/$1" ] && [ "$(cat "$STATE/built/$1")" = "$2" ]; then
		say "unchanged: $1 already built at $2"
		return 1
	fi
	return 0
}

mark_built() { # <name> <key>
	if [ "$DRY" -eq 1 ]; then return 0; fi
	install -d -m 0755 "$STATE/built"
	printf '%s\n' "$2" >"$STATE/built/$1"
}

build_radio() {
	step "radio programs (built from source at the pinned commits)"
	if [ "$SKIP_BUILD" -eq 1 ]; then
		say "skipped (--skip-build)"
		return 0
	fi
	# Pi-Star's own binaries (Pi-Star_v43_Binaries_Bin) are 32-bit ARM
	# hard-float executables linked against libwiringPi / libArduiPi_OLED;
	# they are not used on this arm64 system.
	local jobs gps_key="nogpsd"
	jobs="$(nproc 2>/dev/null || echo 2)"
	# The gateways' Makefiles carry a commented-out second CFLAGS / LIBS
	# pair for gpsd; passing the same values on the make command line
	# selects it without editing the file.
	local -a gps=()
	if [ "$WITH_GPSD" -eq 1 ]; then
		gps=("CFLAGS=-g -O3 -Wall -DHAVE_LOG_H -DUSE_GPSD -std=c++0x -pthread" "LIBS=-lm -lpthread -lgps")
		gps_key="gpsd"
	fi

	if need_build MMDVMHost "$PIN_MMDVMHOST"; then
		clone_pinned "$URL_MMDVMHOST" "$SRC/MMDVMHost" "$PIN_MMDVMHOST"
		# Plain "Makefile": no HD44780 / OLED / wiringPi, built-in Nextion
		# driver included. Builds MMDVMHost and RemoteCommand.
		run make -C "$SRC/MMDVMHost" -j"$jobs"
		put "$SRC/MMDVMHost/MMDVMHost" /usr/local/bin/MMDVMHost 0755
		put "$SRC/MMDVMHost/RemoteCommand" /usr/local/bin/RemoteCommand 0755
		mark_built MMDVMHost "$PIN_MMDVMHOST"
	fi

	if need_build DMRGateway "$PIN_DMRGATEWAY $gps_key"; then
		clone_pinned "$URL_DMRGATEWAY" "$SRC/DMRGateway" "$PIN_DMRGATEWAY"
		run make -C "$SRC/DMRGateway" -j"$jobs" "${gps[@]}"
		put "$SRC/DMRGateway/DMRGateway" /usr/local/bin/DMRGateway 0755
		mark_built DMRGateway "$PIN_DMRGATEWAY $gps_key"
	fi

	if need_build YSFClients "$PIN_YSFCLIENTS $gps_key"; then
		clone_pinned "$URL_YSFCLIENTS" "$SRC/YSFClients" "$PIN_YSFCLIENTS"
		run make -C "$SRC/YSFClients/YSFGateway" -j"$jobs" "${gps[@]}"
		run make -C "$SRC/YSFClients/DGIdGateway" -j"$jobs" "${gps[@]}"
		run make -C "$SRC/YSFClients/YSFParrot" -j"$jobs"
		put "$SRC/YSFClients/YSFGateway/YSFGateway" /usr/local/bin/YSFGateway 0755
		put "$SRC/YSFClients/DGIdGateway/DGIdGateway" /usr/local/bin/DGIdGateway 0755
		put "$SRC/YSFClients/YSFParrot/YSFParrot" /usr/local/bin/YSFParrot 0755
		mark_built YSFClients "$PIN_YSFCLIENTS $gps_key"
	fi

	if need_build P25Clients "$PIN_P25CLIENTS"; then
		clone_pinned "$URL_P25CLIENTS" "$SRC/P25Clients" "$PIN_P25CLIENTS"
		run make -C "$SRC/P25Clients/P25Gateway" -j"$jobs"
		run make -C "$SRC/P25Clients/P25Parrot" -j"$jobs"
		put "$SRC/P25Clients/P25Gateway/P25Gateway" /usr/local/bin/P25Gateway 0755
		put "$SRC/P25Clients/P25Parrot/P25Parrot" /usr/local/bin/P25Parrot 0755
		mark_built P25Clients "$PIN_P25CLIENTS"
	fi

	if need_build NXDNClients "$PIN_NXDNCLIENTS $gps_key"; then
		clone_pinned "$URL_NXDNCLIENTS" "$SRC/NXDNClients" "$PIN_NXDNCLIENTS"
		run make -C "$SRC/NXDNClients/NXDNGateway" -j"$jobs" "${gps[@]}"
		run make -C "$SRC/NXDNClients/NXDNParrot" -j"$jobs"
		put "$SRC/NXDNClients/NXDNGateway/NXDNGateway" /usr/local/bin/NXDNGateway 0755
		put "$SRC/NXDNClients/NXDNParrot/NXDNParrot" /usr/local/bin/NXDNParrot 0755
		mark_built NXDNClients "$PIN_NXDNCLIENTS $gps_key"
	fi

	if need_build M17Gateway "$PIN_M17GATEWAY $gps_key"; then
		clone_pinned "$URL_M17GATEWAY" "$SRC/M17Gateway" "$PIN_M17GATEWAY"
		run make -C "$SRC/M17Gateway" -j"$jobs" "${gps[@]}"
		put "$SRC/M17Gateway/M17Gateway" /usr/local/bin/M17Gateway 0755
		mark_built M17Gateway "$PIN_M17GATEWAY $gps_key"
	fi

	local name url pin
	for name in DAPNETGateway APRSGateway MMDVMCal NextionDriver; do
		case "$name" in
		DAPNETGateway) url="$URL_DAPNETGATEWAY" pin="$PIN_DAPNETGATEWAY" ;;
		APRSGateway) url="$URL_APRSGATEWAY" pin="$PIN_APRSGATEWAY" ;;
		MMDVMCal) url="$URL_MMDVMCAL" pin="$PIN_MMDVMCAL" ;;
		NextionDriver) url="$URL_NEXTIONDRIVER" pin="$PIN_NEXTIONDRIVER" ;;
		esac
		if need_build "$name" "$pin"; then
			clone_pinned "$url" "$SRC/$name" "$pin"
			run make -C "$SRC/$name" -j"$jobs"
			put "$SRC/$name/$name" "/usr/local/bin/$name" 0755
			mark_built "$name" "$pin"
		fi
	done

	# Cross-mode programs of MMDVM_CM that Pi-Star ships and the dashboard
	# offers.
	if need_build MMDVM_CM "$PIN_MMDVM_CM"; then
		clone_pinned "$URL_MMDVM_CM" "$SRC/MMDVM_CM" "$PIN_MMDVM_CM"
		for name in YSF2DMR YSF2NXDN YSF2P25 DMR2YSF DMR2NXDN NXDN2DMR; do
			run make -C "$SRC/MMDVM_CM/$name" -j"$jobs"
			put "$SRC/MMDVM_CM/$name/$name" "/usr/local/bin/$name" 0755
		done
		mark_built MMDVM_CM "$PIN_MMDVM_CM"
	fi

	if [ "$WITH_DSTAR" -eq 1 ]; then
		# ASSUMPTION: Pi-Star's build settings for ircDDBGateway are not
		# published. The directories below are inferred from where the
		# dashboard and the service wrapper look (config in /etc, logs in
		# /var/log/pi-star, host files in /usr/local/etc).
		if need_build ircDDBGateway "$PIN_IRCDDBGATEWAY"; then
			clone_pinned "$URL_IRCDDBGATEWAY" "$SRC/ircDDBGateway" "$PIN_IRCDDBGATEWAY"
			run make -C "$SRC/ircDDBGateway" -j"$jobs" BUILD=release \
				LOGDIR="$LOGDIR" CONFDIR=/etc DATADIR="$ETC_SHARE"
			put "$SRC/ircDDBGateway/ircDDBGateway/ircddbgatewayd" /usr/local/bin/ircddbgatewayd 0755
			put "$SRC/ircDDBGateway/RemoteControl/remotecontrold" /usr/local/bin/remotecontrold 0755
			put "$SRC/ircDDBGateway/TimeServer/timeserverd" /usr/local/bin/timeserverd 0755
			put "$SRC/ircDDBGateway/StarNetServer/starnetserverd" /usr/local/bin/starnetserverd 0755
			mark_built ircDDBGateway "$PIN_IRCDDBGATEWAY"
		fi
	fi
}

data_files() {
	step "data files -> $ETC_SHARE"
	local pair src dst f
	if [ -f "$SRC/MMDVMHost/RSSI.dat" ] || [ "$DRY" -eq 1 ]; then
		put_conf "$SRC/MMDVMHost/RSSI.dat" "$ETC_SHARE/RSSI.dat" 0644 || true
	fi
	# Voice prompts of the gateways (GPL sources, copied from the builds).
	for pair in "DMRGateway/Audio:DMR_Audio" "P25Clients/P25Gateway/Audio:P25_Audio" \
		"NXDNClients/NXDNGateway/Audio:NXDN_Audio" "M17Gateway/Audio:M17_Audio"; do
		src="$SRC/${pair%%:*}"
		dst="$ETC_SHARE/${pair##*:}"
		if [ -d "$dst" ]; then
			say "kept:      $dst"
		elif [ -d "$src" ] || [ "$DRY" -eq 1 ]; then
			say "install:   $dst"
			run cp -r "$src" "$dst"
			record "$dst/"
		else
			say "skipped:   $dst ($src not present - built with --skip-build?)"
		fi
	done
	# HostFilesUpdate.sh makes a dated copy of each list before fetching a
	# new one; start with empty files so that the first run is quiet.
	for f in APRSHosts.txt DCS_Hosts.txt DExtra_Hosts.txt DMRIds.dat DMR_Hosts.txt \
		DPlus_Hosts.txt P25Hosts.txt P25HostsLocal.txt M17Hosts.txt YSFHosts.txt FCSHosts.txt \
		XLXHosts.txt NXDN.csv NXDNHosts.txt NXDNHostsLocal.txt TGList_BM.txt TGList_P25.txt \
		TGList_NXDN.txt TGList_YSF.txt; do
		if [ ! -e "$ETC_SHARE/$f" ]; then
			run touch "$ETC_SHARE/$f"
			record "$ETC_SHARE/$f" "$MANIFEST_CONF"
		fi
	done
}

configs() {
	step "configuration files -> /etc (existing files are never replaced)"
	local tmp f new_mmdvm=0
	if [ "$DRY" -eq 1 ]; then
		say "  would run: unzip $SRC/bin/config_clean.zip into a temporary directory and"
		say "             install each file as /etc/<name> (mode 644) unless it exists:"
		say "             mmdvmhost dmrgateway ysfgateway p25gateway nxdngateway dgidgateway"
		say "             ysf2dmr ysf2nxdn ysf2p25 dmr2ysf dmr2nxdn ircddbgateway dstarrepeater"
		say "             starnetserver timeserver pistar-remote"
		new_mmdvm=1
	else
		tmp="$(mktemp -d)"
		unzip -q -o "$SRC/bin/config_clean.zip" -d "$tmp"
		for f in "$tmp"/*; do
			[ -f "$f" ] || continue
			if put_conf "$f" "/etc/$(basename "$f")" 0644; then
				if [ "$(basename "$f")" = mmdvmhost ]; then new_mmdvm=1; fi
			fi
		done
		rm -rf "$tmp"
	fi

	# Three gateways have no file in config_clean.zip; Pi-Star images carry
	# one. The sample of the pinned source is used instead, switched to
	# daemon mode and Pi-Star's log directory. The dashboard shows the
	# matching sections only when the file exists.
	local name ini
	for name in M17Gateway DAPNETGateway APRSGateway; do
		ini="$SRC/$name/$name.ini"
		f="/etc/$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
		if [ "$DRY" -eq 0 ] && [ ! -f "$ini" ]; then
			say "skipped:   $f ($ini not present)"
			continue
		fi
		if put_conf "$ini" "$f" 0644; then
			run "$PRESETS" --set "$f" General Daemon 1
			run "$PRESETS" --set "$f" Log FilePath "$LOGDIR"
			run "$PRESETS" --set "$f" Log DisplayLevel 0
			if [ "$name" = M17Gateway ]; then
				run "$PRESETS" --set "$f" Network HostsFile1 "$ETC_SHARE/M17Hosts.txt"
			fi
		fi
	done

	# /etc/pistar-release: read by the dashboard ([Pi-Star] Version) and by
	# the scripts (awk on "Version" / "Hardware"; there must be exactly one
	# line containing each word).
	write_conf /etc/pistar-release 0644 <<EOF
[Pi-Star]
Version = $PISTAR_VERSION
Hardware = Bubblegum96
EOF

	# Board facts in /etc/mmdvmhost. A file created just now also gets the
	# first-install choices (duplex, Nextion, layout 3); an existing one
	# only the wiring facts.
	if [ "$new_mmdvm" -eq 1 ]; then
		run "$PRESETS" --defaults
	elif [ -f /etc/mmdvmhost ]; then
		run "$PRESETS" --hardware
	fi
}

# --- systemd -----------------------------------------------------------------

# Pi-Star's unit files are part of its image, not of a repository. The
# pattern is visible in pistar-upgrade, which creates several of them
# (Type=forking, ExecStart=/usr/local/sbin/<name>.service start, and a
# <name>.timer with OnStartupSec that is enabled instead of the service).
# The same pattern is generated here for every wrapper that was installed.
unit_pair() { # <name> <description> <startup seconds> [extra After/Wants]
	local name="$1" desc="$2" sec="$3" extra="${4:-}"
	write_file "$UNIT_DIR/$name.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
# The decision whether the daemon runs is made by the Pi-Star wrapper
# /usr/local/sbin/$name.service (mode enabled, configured, ...).
[Unit]
Description=Pi-Star $desc
After=network.target ${extra}
${extra:+Wants=${extra}}

[Service]
Type=forking
ExecStart=/usr/local/sbin/$name.service start
ExecStop=/usr/local/sbin/$name.service stop
ExecReload=/usr/local/sbin/$name.service restart

[Install]
WantedBy=multi-user.target
EOF
	write_file "$UNIT_DIR/$name.timer" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
# The dashboard edits OnStartupSec of mmdvmhost.timer with sed.
[Timer]
OnStartupSec=$sec

[Install]
WantedBy=multi-user.target
EOF
	TIMERS+=("$name.timer")
}

systemd_units() {
	step "systemd units ($UNIT_DIR, Pi-Star's unit names)"
	local u
	# Units of the minimal package with the same names live in
	# /etc/systemd/system and would take precedence.
	for u in mmdvmhost.service dmrgateway.service ysfgateway.service; do
		displace "/etc/systemd/system/$u"
	done

	TIMERS=()
	# The modem's BOOT0 / reset lines are put into their idle state by
	# mmdvm-gpio-init.service of ../install.sh before MMDVMHost starts.
	unit_pair mmdvmhost "MMDVMHost" 30 mmdvm-gpio-init.service
	unit_pair dmrgateway "DMRGateway" 20
	unit_pair ysfgateway "YSFGateway" 20
	unit_pair ysfparrot "YSFParrot" 20
	unit_pair dgidgateway "DGIdGateway" 20
	unit_pair p25gateway "P25Gateway" 20
	unit_pair p25parrot "P25Parrot" 20
	unit_pair nxdngateway "NXDNGateway" 20
	unit_pair nxdnparrot "NXDNParrot" 20
	unit_pair m17gateway "M17Gateway" 20
	unit_pair dapnetgateway "DAPNETGateway" 20
	unit_pair aprsgateway "APRSGateway" 20
	unit_pair ysf2dmr "YSF2DMR" 20
	unit_pair ysf2nxdn "YSF2NXDN" 20
	unit_pair ysf2p25 "YSF2P25" 20
	unit_pair dmr2ysf "DMR2YSF" 20
	unit_pair dmr2nxdn "DMR2NXDN" 20
	unit_pair nxdn2dmr "NXDN2DMR" 20
	if [ "$WITH_DSTAR" -eq 1 ]; then
		unit_pair ircddbgateway "ircDDBGateway" 20
		unit_pair timeserver "D-Star TimeServer" 30
	fi

	# NextionDriver: only runs when [Nextion] Port=/dev/ttyNextionDriver
	# (the wrapper checks); with Port=modem it stays off.
	write_file "$UNIT_DIR/nextiondriver.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Unit]
Description=Pi-Star NextionDriver
Before=mmdvmhost.service
After=local-fs.target

[Service]
Type=forking
WorkingDirectory=$ETC_SHARE
ExecStart=/usr/local/sbin/nextiondriver.service start
ExecStop=/usr/local/sbin/nextiondriver.service stop
ExecReload=/usr/local/sbin/nextiondriver.service reload

[Install]
WantedBy=multi-user.target
EOF

	# Watchdog: board/pistar-watchdog (bash) instead of the Python 2 one.
	write_file "$UNIT_DIR/pistar-watchdog.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Unit]
Description=Pi-Star watchdog (Bubblegum-96 replacement)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/sbin/pistar-watchdog
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
	write_file "$UNIT_DIR/pistar-watchdog.timer" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Timer]
OnStartupSec=60

[Install]
WantedBy=multi-user.target
EOF
	TIMERS+=(pistar-watchdog.timer)

	# uPnP port mapping: present because the dashboard's firewall section
	# switches it; NOT enabled here. It runs only after "uPNP: On" is
	# chosen in the dashboard.
	write_file "$UNIT_DIR/pistar-upnp.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Unit]
Description=Pi-Star uPnP port mappings (off unless enabled in the dashboard)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=true
ExecStart=/usr/local/sbin/pistar-upnp.service start
ExecStopPost=/usr/local/sbin/pistar-upnp.service stop

[Install]
WantedBy=multi-user.target
EOF
	write_file "$UNIT_DIR/pistar-upnp.timer" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Timer]
OnStartupSec=60

[Install]
WantedBy=multi-user.target
EOF

	if [ "$WITH_FIREWALL" -eq 1 ]; then
		adapt_firewall
	fi

	run systemctl daemon-reload
	# As on Pi-Star the timers are enabled, not the services. Nothing is
	# started now; the services come up at the next boot.
	run systemctl enable "${TIMERS[@]}" nextiondriver.service
}

# Pi-Star's firewall script flushes all iptables rules and sets INPUT and
# OUTPUT to DROP with its own allow list. It is used unchanged, and only on
# request (--with-firewall): on a general Ubuntu system it would also replace
# whatever rules exist. Without the option no port is opened or closed.
adapt_firewall() {
	if have ufw && ufw status 2>/dev/null | grep -q '^Status: active'; then
		die "--with-firewall: ufw is active; pistar-firewall would wipe its rules. Disable ufw or drop the option."
	fi
	write_file "$UNIT_DIR/pistar-b96-firewall.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh (--with-firewall).
# UNTESTED. Runs Pi-Star's iptables script, unchanged, once per boot.
[Unit]
Description=Pi-Star firewall (iptables rules of pistar-firewall)
Wants=network-pre.target
Before=network-pre.target
DefaultDependencies=no
After=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=true
ExecStart=/usr/local/sbin/pistar-firewall

[Install]
WantedBy=multi-user.target
EOF
	TIMERS+=(pistar-b96-firewall.service)
}

# --- web server ----------------------------------------------------------------

web_server() {
	step "nginx + php-fpm"
	local phpver="8.3"
	if [ "$DRY" -eq 0 ]; then
		have php || die "php is not installed (run without --skip-apt)"
		phpver="$(php -r 'echo PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION;')"
		[ -d "/etc/php/$phpver/fpm" ] || die "/etc/php/$phpver/fpm not found (php-fpm not installed?)"
	fi

	# Pi-Star's site file is part of its image. What is known from the
	# upstream scripts: document root /var/www/dashboard, a "location ^~
	# /admin" block with client_max_body_size 512K, php through an included
	# snippet, /.git denied, listening on 80 for IPv4 and IPv6. The admin
	# tree is behind HTTP basic authentication against /var/www/.htpasswd
	# (the dashboard maintains that file with htpasswd).
	write_file /etc/nginx/sites-available/pi-star 0644 <<EOF
# Pi-Star dashboard on the Bubblegum-96.
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
server {
	listen 80 default_server;
	listen [::]:80 default_server;
	server_name _;

	root $DASH;
	index index.php index.html;

	# The dashboard is a git checkout; never serve its metadata, nor
	# the password file one directory up.
	location ~ /\.(git|ht) {
		deny all;
	}

	# Everything below /admin needs the admin login.
	location ^~ /admin {
		auth_basic "Pi-Star";
		auth_basic_user_file /var/www/.htpasswd;
		client_max_body_size 512K;
		try_files \$uri \$uri/ =404;

		location ~ /\.(git|ht) {
			deny all;
		}
		location ~ \.php\$ {
			include snippets/fastcgi-php.conf;
			fastcgi_pass unix:/run/php/php$phpver-fpm.sock;
			fastcgi_read_timeout 300;
		}
	}

	location / {
		try_files \$uri \$uri/ =404;
	}

	location ~ \.php\$ {
		include snippets/fastcgi-php.conf;
		fastcgi_pass unix:/run/php/php$phpver-fpm.sock;
		fastcgi_read_timeout 300;
	}
}
EOF
	# Ubuntu's default site also claims "default_server" on port 80.
	displace /etc/nginx/sites-enabled/default
	if [ ! -L /etc/nginx/sites-enabled/pi-star ]; then
		displace /etc/nginx/sites-enabled/pi-star
		run ln -s ../sites-available/pi-star /etc/nginx/sites-enabled/pi-star
		record /etc/nginx/sites-enabled/pi-star
	fi

	# Same PHP hardening Pi-Star 4.3.10 applies (pistar-upgrade, arm 4.3.9).
	write_file "/etc/php/$phpver/fpm/conf.d/99-pistar-hardening.ini" 0644 <<EOF
; Pi-Star PHP hardening (as pistar-upgrade 4.3.9 -> 4.3.10 does).
session.upload_progress.enabled = 0
EOF

	web_password

	if [ "$DRY" -eq 1 ]; then
		say "  would run: nginx -t; systemctl enable nginx php$phpver-fpm; systemctl restart php$phpver-fpm nginx"
		return 0
	fi
	nginx -t || die "nginx rejects the configuration (see the message above); nothing restarted"
	systemctl enable nginx "php$phpver-fpm"
	systemctl restart "php$phpver-fpm"
	systemctl restart nginx
}

# /var/www/.htpasswd for user pi-star. The password is read without echo and
# piped to htpasswd; it is never written to a log, the terminal or a file
# other than the hash in .htpasswd.
web_password() {
	local f=/var/www/.htpasswd pw="" pw2=""
	if [ -e "$f" ]; then
		say "kept:      $f (web admin password unchanged)"
		return 0
	fi
	if [ "$DRY" -eq 1 ]; then
		say "  would create: $f for web user '$PISTAR_WEB_USER' (prompt without echo;"
		say "                empty input = Pi-Star's default password, which the dashboard"
		say "                then asks to change)"
		return 0
	fi
	if [ -t 0 ]; then
		say ""
		say "Web admin login: user '$PISTAR_WEB_USER'. Type a password now, or press Enter to"
		say "start with Pi-Star's default password (see README.md) and change it in the"
		say "dashboard, which will insist on that."
		read -r -s -p "Password: " pw
		printf '\n'
		if [ -n "$pw" ]; then
			read -r -s -p "Again:    " pw2
			printf '\n'
			[ "$pw" = "$pw2" ] || die "the two passwords differ; nothing written, run the installer again"
		fi
	fi
	if [ -z "$pw" ]; then
		pw="$PISTAR_DEFAULT_WEB_PASSWORD"
		say "Using Pi-Star's default web password. CHANGE IT on the configuration page."
	fi
	(
		umask 077
		: >"$f"
	)
	printf '%s\n' "$pw" | htpasswd -i "$f" "$PISTAR_WEB_USER" >/dev/null 2>&1 ||
		{
			rm -f "$f"
			die "htpasswd failed"
		}
	pw=""
	pw2=""
	# www-data: nginx reads the file, and the dashboard rewrites it with
	# htpasswd (without sudo) when the password is changed.
	chown www-data:www-data "$f"
	chmod 0600 "$f"
	record "$f" "$MANIFEST_CONF"
	say "install:   $f"
}

# --- sudo ----------------------------------------------------------------------

# The dashboard changes the system through sudo. Pi-Star (since 4.1.11 /
# 4.3.x) no longer gives www-data "NOPASSWD: ALL" but a command allowlist,
# /etc/sudoers.d/pistar-dashboard, which pistar-upgrade writes line by line
# in its function deploy_sudoers_tightening(). That list is the authoritative
# statement of what the pinned dashboard needs, so it is taken from the
# pinned script itself: the "echo '...' >> ${stage}" lines of that function
# are extracted as text (nothing of the script is executed) and checked with
# visudo. One line is changed: the permission for "mount -o remount,ro /" is
# dropped, since the dashboard no longer calls it here.
sudoers() {
	step "sudoers"
	local src="$SRC/sbin/pistar-upgrade" stage
	if [ "$DRY" -eq 1 ]; then
		say "  would run: extract the allowlist from $src, drop the 'remount,ro' entry,"
		say "             visudo -c -f, install as /etc/sudoers.d/pistar-dashboard (0440)"
		say "  would write: /etc/sudoers.d/pistar-b96 (0440): www-data may run"
		say "             $PRESETS --hardware"
		return 0
	fi
	stage="$(mktemp)"
	build_sudoers "$src" >"$stage"
	[ "$(wc -l <"$stage")" -ge 100 ] ||
		die "sudoers allowlist extraction from pistar-upgrade gave too little (upstream changed?)"
	grep -q '^www-data ALL=(root) NOPASSWD: PISTAR_DASH_ALL$' "$stage" ||
		die "sudoers allowlist: the www-data rule is missing (upstream changed?)"
	if grep -q 'remount\\,ro' "$stage"; then
		die "sudoers allowlist: remount,ro entry still present"
	fi
	visudo -c -f "$stage" >/dev/null || die "visudo rejects the extracted allowlist"
	put "$stage" /etc/sudoers.d/pistar-dashboard 0440
	rm -f "$stage"

	stage="$(mktemp)"
	cat >"$stage" <<EOF
# Bubblegum-96 port of Pi-Star (software/bubblegum96/pistar).
# The patched restore page re-applies the board's wiring facts
# (patches/dashboard/0001-config-backup-reapply-board-presets.patch).
www-data ALL=(root) NOPASSWD: $PRESETS --hardware
EOF
	visudo -c -f "$stage" >/dev/null || die "visudo rejects /etc/sudoers.d/pistar-b96"
	put "$stage" /etc/sudoers.d/pistar-b96 0440
	rm -f "$stage"
	visudo -c >/dev/null || die "visudo -c fails with the new files in place; remove /etc/sudoers.d/pistar-*"
}

# build_sudoers <pistar-upgrade>: print the allowlist on stdout.
build_sudoers() {
	awk '/^deploy_sudoers_tightening\(\) \{/ { f = 1 } f && /# Validate the staged spec/ { exit } f' "$1" |
		sed -n -E "s/^[[:space:]]*echo '(.*)'[[:space:]]*>>?[[:space:]]*[$][{]stage[}][[:space:]]*\$/\\1/p" |
		sed -e 's#^\([[:space:]]*/bin/mount -o remount\\,rw /\), \\$#\1#' \
			-e '/^[[:space:]]*\/bin\/mount -o remount\\,ro \/$/d'
}

# --- cron, logs ------------------------------------------------------------------

cron_and_logs() {
	step "cron, log handling"
	# One daily job (host files, old daemon logs) at a time chosen once per
	# installation, as Pi-Star shuffles its daily job. Pi-Star's hourly job
	# (journal vacuum to 5 MB, remount read-only) is not reproduced.
	write_conf /etc/cron.d/pistar-b96 0644 <<EOF
# Pi-Star port on the Bubblegum-96: daily host file refresh and log clean-up.
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
$((RANDOM % 60)) $((3 + RANDOM % 3)) * * * root /usr/local/sbin/pistar-b96-daily >/dev/null 2>&1
EOF

	# The dashboard shows "uPNP: On" unless /etc/crontab has a commented
	# pistar-upnp line, and its On/Off switch edits that line. Add it
	# commented, i.e. off.
	local line='#*/5 *	* * *	root	/usr/local/sbin/pistar-upnp.service start > /dev/null 2>&1 &'
	if [ -f /etc/crontab ] && ! grep -q 'pistar-upnp.service' /etc/crontab; then
		say "edit:      /etc/crontab (one commented pistar-upnp line appended)"
		if [ "$DRY" -eq 0 ]; then
			printf '%s\n' "$line" >>/etc/crontab
			touch "$STATE/crontab-line-added"
		fi
	fi

	# Daemon logs are dated files removed by the daily job. The script logs
	# (update, upgrade, modem flash, jitter test) are truncated by the
	# dashboard before each use; rotate them anyway.
	write_file /etc/logrotate.d/pistar-b96 0644 <<EOF
$LOGDIR/pi-star_*.log {
	weekly
	rotate 2
	missingok
	notifempty
	copytruncate
	su root mmdvm
}
EOF
}

# --- board adaptations -----------------------------------------------------------

# Modem port. Pi-Star's configuration page writes /dev/ttyAMA0 into
# /etc/mmdvmhost for every "GPIO" modem type (admin/configure.php), and the
# calibration tools read the port from there. Instead of changing dozens of
# places, the S900 UART gets that name as an alias: the S900 has no AMBA
# PL011 UART, so the kernel never creates a real ttyAMA0 here.
# The group matters as well: MMDVMHost running as a daemon switches to user
# mmdvm with only that user's primary group (setgid/setuid, no initgroups).
adapt_modem_port() {
	step "modem port: /dev/ttyAMA0 -> /dev/$MODEM_TTY"
	if [ -c /dev/ttyAMA0 ] && [ ! -L /dev/ttyAMA0 ]; then
		die "/dev/ttyAMA0 is a real device on this kernel; the alias cannot be used. See README.md."
	fi
	write_file /etc/udev/rules.d/99-pistar-b96-modem.rules 0644 <<EOF
# Pi-Star port on the Bubblegum-96: the MMDVM_HS modem UART under the name
# Pi-Star's pages use, accessible to the mmdvm service user. UNTESTED.
SUBSYSTEM=="tty", KERNEL=="$MODEM_TTY", SYMLINK+="ttyAMA0", GROUP="mmdvm", MODE="0660"
EOF
	run udevadm control --reload-rules
	run udevadm trigger --subsystem-match=tty --action=change
}

# Wi-Fi. Pi-Star's Wi-Fi page writes /etc/wpa_supplicant/wpa_supplicant.conf
# and expects an interface called wlan0 run by wpa_supplicant (on the Pi:
# dhcpcd's hook). On Ubuntu the same file is used through the stock
# wpa_supplicant@wlan0.service; systemd-networkd (via a netplan file) does
# DHCP; a path unit makes wpa_supplicant re-read the file when the page saves
# it. Skipped if the system already manages Wi-Fi itself.
adapt_wifi() {
	step "Wi-Fi (wpa_supplicant@$WIFI_IF, netplan DHCP)"
	if have systemctl && systemctl is-active --quiet NetworkManager 2>/dev/null; then
		warn "NetworkManager is active: Wi-Fi is left alone; the dashboard's Wi-Fi page will not work"
		return 0
	fi
	if grep -rqs '^[[:space:]]*wifis:' /etc/netplan 2>/dev/null; then
		warn "netplan already configures Wi-Fi: left alone; the dashboard's Wi-Fi page will not work"
		return 0
	fi

	local other=""
	if [ ! -e "/sys/class/net/$WIFI_IF" ]; then
		other="$(find /sys/class/net -maxdepth 1 -name 'wl*' 2>/dev/null | head -n 1 || true)"
		if [ -n "$other" ]; then
			say "Wi-Fi interface is $(basename "$other"); it will be named $WIFI_IF after a reboot"
			write_file /etc/systemd/network/10-pistar-b96-wlan.link 0644 <<EOF
# Pi-Star port: the dashboard's Wi-Fi page is written for "wlan0". UNTESTED.
# Assumes one Wi-Fi interface.
[Match]
Type=wlan

[Link]
Name=$WIFI_IF
EOF
		else
			warn "no Wi-Fi interface found; the files are installed anyway"
		fi
	fi

	run groupadd -f netdev
	run install -d -m 0755 /etc/wpa_supplicant
	write_conf /etc/wpa_supplicant/wpa_supplicant.conf 0600 <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
ap_scan=1
fast_reauth=1
EOF
	# wpa_supplicant@.service reads wpa_supplicant-<interface>.conf.
	if [ ! -e "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" ] && [ ! -L "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" ]; then
		run ln -s wpa_supplicant.conf "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf"
		record "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf"
	fi

	write_conf /etc/netplan/61-pistar-b96-wlan.yaml 0600 <<EOF
# Pi-Star port: DHCP on the Wi-Fi interface. Association is done by
# wpa_supplicant@$WIFI_IF.service with /etc/wpa_supplicant/wpa_supplicant.conf
# (the file the dashboard writes), which is why the interface is listed
# here as a plain device and not under "wifis". UNTESTED.
network:
  version: 2
  ethernets:
    $WIFI_IF:
      dhcp4: true
      dhcp6: true
      optional: true
EOF

	write_file "$UNIT_DIR/pistar-b96-wifi.path" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Unit]
Description=Pi-Star port: watch the Wi-Fi configuration written by the dashboard

[Path]
PathChanged=/etc/wpa_supplicant/wpa_supplicant.conf

[Install]
WantedBy=multi-user.target
EOF
	write_file "$UNIT_DIR/pistar-b96-wifi.service" 0644 <<EOF
# Generated by software/bubblegum96/pistar/install-pistar.sh. UNTESTED.
[Unit]
Description=Pi-Star port: make wpa_supplicant re-read its configuration

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/sbin/wpa_cli -i $WIFI_IF reconfigure || /usr/bin/systemctl try-restart wpa_supplicant@$WIFI_IF.service'
EOF

	# Country list of the Wi-Fi page: Pi-Star reads /lib/crda/db.txt (lines
	# "country XX: ...") and falls back to six countries without Taiwan.
	# Build the list from the ISO 3166 table of tzdata; it is a list of
	# codes only, the kernel's regulatory database decides what is allowed.
	if [ ! -e /lib/crda/db.txt ] && [ ! -e /lib/crda/regulatory.bin ]; then
		if [ "$DRY" -eq 1 ]; then
			say "  would write: /lib/crda/db.txt (country codes from /usr/share/zoneinfo/iso3166.tab)"
		elif [ -r /usr/share/zoneinfo/iso3166.tab ]; then
			local tmp
			tmp="$(mktemp)"
			awk -F '\t' '/^[A-Z][A-Z]\t/ { print "country " $1 ":" }' /usr/share/zoneinfo/iso3166.tab >"$tmp"
			put "$tmp" /lib/crda/db.txt 0644
			rm -f "$tmp"
		fi
	fi

	run systemctl daemon-reload
	run systemctl enable "wpa_supplicant@$WIFI_IF.service" pistar-b96-wifi.path
	if [ "$DRY" -eq 0 ] && have netplan; then
		netplan generate || warn "netplan generate failed; check /etc/netplan/61-pistar-b96-wlan.yaml"
	fi
	say "Wi-Fi takes effect after a reboot (or: netplan apply; systemctl start wpa_supplicant@$WIFI_IF pistar-b96-wifi.path)"
}

# Host name. Pi-Star images are called "pi-star"; the dashboard's host name
# field edits /etc/hostname and /etc/hosts with sed, replacing the old name.
# The name is only changed here when asked for.
adapt_hostname() {
	local cur
	cur="$(hostname 2>/dev/null || echo unknown)"
	if [ -n "$NEW_HOSTNAME" ] && [ "$NEW_HOSTNAME" != "$cur" ]; then
		step "host name -> $NEW_HOSTNAME"
		run hostnamectl set-hostname "$NEW_HOSTNAME"
		if [ "$DRY" -eq 0 ]; then
			if grep -qw -- "$cur" /etc/hosts; then
				sed -i "s/\\b$cur\\b/$NEW_HOSTNAME/g" /etc/hosts
			else
				printf '127.0.1.1\t%s\n' "$NEW_HOSTNAME" >>/etc/hosts
			fi
		fi
	elif [ -r /etc/hosts ] && ! grep -qw -- "$cur" /etc/hosts; then
		warn "/etc/hosts has no entry for '$cur'; the dashboard's host name field edits that entry"
	fi
}

first_hostfiles() {
	step "host files (www.pistar.uk, by Pi-Star's own HostFilesUpdate.sh)"
	if [ "$DRY" -eq 1 ]; then
		say "  would run: /usr/local/sbin/HostFilesUpdate.sh (best effort)"
		return 0
	fi
	/usr/local/sbin/HostFilesUpdate.sh >/dev/null 2>&1 ||
		warn "HostFilesUpdate.sh failed (no network?); run 'sudo pistar-update' later"
}

summary() {
	cat <<EOF

Done$([ "$DRY" -eq 1 ] && echo " (dry run: nothing was changed)").

Next steps (README.md, configure-brandmeister.md):
  1. Reboot. (The Pi-Star timers start the services after boot; the radio
     services stay off until the configuration page has been saved once.)
  2. Browse to http://<address of this board>/ ; the admin pages ask for the
     login 'pi-star'. Change the password on the Configuration page.
  3. Configuration: Controller Software = MMDVMHost, Controller Mode = Duplex
     Repeater, Radio/Modem Type = "MMDVM_HS_Duplex_Hat (DB9MAT, DF2ET & DO7EN)
     for Pi (GPIO)".
  4. If something does not work: /var/log/nginx/error.log first.

This installation is UNTESTED; see the list of assumptions in README.md.
EOF
}

main() {
	parse_args "$@"
	preflight
	apt_packages
	users_and_dirs
	fetch_pistar
	install_scripts
	build_radio
	data_files
	configs
	adapt_modem_port
	systemd_units
	sudoers
	web_server
	cron_and_logs
	adapt_wifi
	adapt_hostname
	first_hostfiles
	summary
}

# PISTAR_INSTALL_LIB_ONLY=1: define the functions and stop (used to test the
# text-processing functions on a PC).
if [ "${PISTAR_INSTALL_LIB_ONLY:-0}" = 1 ]; then
	return 0 2>/dev/null || exit 0
fi
main "$@"
