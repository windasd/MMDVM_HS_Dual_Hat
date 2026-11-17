#!/usr/bin/env bash
# Remove what install-pistar.sh installed, and only that.
#
# UNTESTED: never run on the target (bash -n only).
#
# Usage: sudo bash uninstall-pistar.sh [--dry-run] [--purge]
#
#   default   removes programs, scripts, units, the dashboard, the nginx
#             site, the sudoers files, cron / logrotate / udev files and the
#             source trees; puts back every file the installer had moved
#             aside (/var/lib/pistar-b96/displaced), e.g. the units and
#             gateway binaries of the minimal package and nginx's default
#             site. KEEPS the configuration it created (/etc/mmdvmhost,
#             /etc/dmrgateway, ..., /var/www/.htpasswd, host files, Wi-Fi
#             configuration) and the users mmdvm / pi-star.
#   --purge   also removes that configuration, files the dashboard created
#             (/etc/dstar-radio.*, API key files, ...), the Wi-Fi set-up and
#             the users the installer created.
#
# Not undone: installed packages; the host name; a line added to /etc/hosts
# by --hostname; iptables rules loaded by --with-firewall (gone after a
# reboot). The decision what was installed comes from
# /var/lib/pistar-b96/manifest and manifest-conf; nothing else is touched.
set -euo pipefail

DRY=0
PURGE=0
STATE=/var/lib/pistar-b96
MANIFEST="$STATE/manifest"
MANIFEST_CONF="$STATE/manifest-conf"
DISPLACED="$STATE/displaced"
UNIT_DIR=/lib/systemd/system
WIFI_IF=wlan0
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
die() {
	printf 'uninstall-pistar: error: %s\n' "$*" >&2
	exit 1
}
run() {
	if [ "$DRY" -eq 1 ]; then
		printf '  would run:'
		printf ' %q' "$@"
		printf '\n'
	else
		"$@"
	fi
}

for arg in "$@"; do
	case "$arg" in
	--dry-run) DRY=1 ;;
	--purge) PURGE=1 ;;
	-h | --help)
		sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*) die "unknown option $arg" ;;
	esac
done

if [ "$DRY" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
	die "run as root (sudo bash $0), or use --dry-run"
fi
[ -f "$MANIFEST" ] || die "$MANIFEST not found: install-pistar.sh has not installed anything here"

# remove_listed <manifest>: delete the paths it names. A trailing slash marks
# a directory created by the installer; only those are removed recursively,
# and only below a few known places.
remove_listed() {
	local m="$1" p
	[ -f "$m" ] || return 0
	while IFS= read -r p; do
		[ -n "$p" ] || continue
		case "$p" in
		*/)
			case "$p" in
			/var/www/dashboard/ | /opt/pistar-b96/ | /usr/local/bin/firmware/ | /var/log/pi-star/ | /usr/local/etc/*_Audio/)
				if [ -d "$p" ]; then
					say "remove:    $p"
					run rm -rf -- "${p%/}"
				fi
				;;
			*) say "skipped:   $p (unexpected directory entry in the manifest)" ;;
			esac
			;;
		/*)
			if [ -e "$p" ] || [ -L "$p" ]; then
				say "remove:    $p"
				run rm -f -- "$p"
			fi
			;;
		*) say "skipped:   $p (not an absolute path)" ;;
		esac
	done <"$m"
}

step "stop and disable the units of this installation"
units=()
while IFS= read -r p; do
	case "$p" in
	"$UNIT_DIR"/*.service | "$UNIT_DIR"/*.timer | "$UNIT_DIR"/*.path) units+=("$(basename "$p")") ;;
	esac
done <"$MANIFEST"
if command -v systemctl >/dev/null 2>&1; then
	for u in "${units[@]}"; do
		run systemctl disable --now "$u" || true
	done
fi

if [ "$PURGE" -eq 1 ] && command -v systemctl >/dev/null 2>&1; then
	if grep -qxF "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" "$MANIFEST"; then
		say "Wi-Fi set-up of the installer is removed (--purge)"
		run systemctl disable --now "wpa_supplicant@$WIFI_IF.service" || true
	fi
fi

step "remove installed files"
# Without --purge the Wi-Fi association keeps working: its symlink is left.
if [ "$PURGE" -eq 0 ] && [ "$DRY" -eq 0 ]; then
	tmp="$(mktemp)"
	grep -vxF "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" "$MANIFEST" >"$tmp" || true
	remove_listed "$tmp"
	rm -f "$tmp"
else
	remove_listed "$MANIFEST"
fi

if [ -f "$STATE/crontab-line-added" ] && [ -f /etc/crontab ]; then
	say "edit:      /etc/crontab (pistar-upnp line removed)"
	run sed -i '/pistar-upnp\.service/d' /etc/crontab
fi

step "configuration"
if [ "$PURGE" -eq 1 ]; then
	remove_listed "$MANIFEST_CONF"
	# Files the dashboard and the scripts create at run time.
	for p in /etc/dstar-radio.mmdvmhost /etc/dstar-radio.dstarrepeater /etc/pistar-css.ini \
		/etc/bmapi.key /etc/dapnetapi.key /etc/tgifapi.key /etc/hostfiles.nodextra \
		/etc/timeserver.dissable /etc/hostap.off /etc/iptables.rules /etc/ip6tables.rules; do
		if [ -e "$p" ]; then
			say "remove:    $p"
			run rm -f -- "$p"
		fi
	done
	# Dated copies HostFilesUpdate.sh leaves next to the host files.
	if [ -f "$MANIFEST_CONF" ]; then
		while IFS= read -r p; do
			case "$p" in
			/usr/local/etc/*) run find /usr/local/etc -maxdepth 1 -type f -name "$(basename "$p").[0-9]*" -delete ;;
			esac
		done <"$MANIFEST_CONF"
	fi
else
	say "kept (use --purge to remove):"
	if [ -f "$MANIFEST_CONF" ]; then
		while IFS= read -r p; do
			if [ -e "$p" ]; then say "  $p"; fi
		done <"$MANIFEST_CONF"
	fi
	say "  files created by the dashboard (/etc/dstar-radio.*, /etc/*api.key, ...)"
fi

step "put back the files that were moved aside"
leftover=0
if [ -d "$DISPLACED" ]; then
	while IFS= read -r -d '' rel; do
		rel="${rel#./}"
		target="/$rel"
		# In a dry run the installed file that took its place is still there.
		if [ "$DRY" -eq 1 ] && grep -qxF -- "$target" "$MANIFEST"; then
			say "restore:   $target"
			continue
		fi
		if [ -e "$target" ] || [ -L "$target" ]; then
			say "NOT restored: $target exists; the original stays in $DISPLACED/$rel"
			leftover=1
			continue
		fi
		say "restore:   $target"
		run install -d -m 0755 "$(dirname "$target")"
		run mv -- "$DISPLACED/$rel" "$target"
	done < <(cd "$DISPLACED" && find . \( -type f -o -type l \) -print0)
fi

if [ "$PURGE" -eq 1 ]; then
	step "users"
	for u in mmdvm pi-star; do
		if [ -f "$STATE/created-user-$u" ] && getent passwd "$u" >/dev/null 2>&1; then
			say "remove:    user $u (created by the installer)"
			run userdel "$u" || true
		fi
	done
fi

step "reload services"
if command -v systemctl >/dev/null 2>&1; then
	run systemctl daemon-reload
	if command -v udevadm >/dev/null 2>&1; then
		run udevadm control --reload-rules
		run udevadm trigger --subsystem-match=tty --action=change
	fi
	if command -v nginx >/dev/null 2>&1; then
		if [ "$DRY" -eq 1 ]; then
			say "  would run: nginx -t && systemctl restart nginx"
		elif nginx -t >/dev/null 2>&1; then
			systemctl restart nginx || true
		else
			say "nginx configuration does not pass 'nginx -t' now; nginx was not restarted"
		fi
	fi
fi

if [ "$DRY" -eq 0 ]; then
	if [ "$leftover" -eq 1 ]; then
		keep="/var/backups/pistar-b96-displaced-$STAMP"
		install -d -m 0755 /var/backups
		mv -- "$DISPLACED" "$keep"
		say "Originals that could not be put back are in $keep"
	fi
	if [ "$PURGE" -eq 1 ]; then
		rm -rf -- "$STATE"
	else
		# Keep the list of configuration files for a later --purge.
		rm -rf -- "$STATE/built" "$DISPLACED"
		: >"$MANIFEST"
		if [ -L "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" ]; then
			printf '%s\n' "/etc/wpa_supplicant/wpa_supplicant-$WIFI_IF.conf" >>"$MANIFEST"
		fi
	fi
fi

cat <<EOF

Done$([ "$DRY" -eq 1 ] && echo " (dry run: nothing was changed)").
Packages installed for Pi-Star (nginx, php-fpm, build tools, ...) were left.
If the minimal package was installed before, its units are back in
/etc/systemd/system; enable them again with:
    sudo systemctl enable --now mmdvmhost mmdvm-display
EOF
