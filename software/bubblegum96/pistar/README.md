# Pi-Star on the Bubblegum-96 mezzanine

An installer that assembles a **Pi-Star 4.3.10** system - the web dashboard
with its configuration and admin pages, the management scripts and the
pre-MQTT MMDVMHost / gateway programs they are written for - on Ubuntu 24.04
arm64, for the r3.0-study board (MMDVM_HS dual hat on `/dev/ttyOWL2`, TJC
display behind the modem, GPS on gpsd).

> ## UNTESTED
>
> **Nothing in this directory has been run on the target.** The board has
> never been built, there was no Bubblegum-96 and no Ubuntu arm64 machine.
> No program was compiled, no page was opened in a browser, no service was
> started, no login to BrandMeister was made.
>
> What was actually done, on a Windows PC with Git Bash:
> - `bash -n` on every script here (all pass);
> - `install-pistar.sh --dry-run` runs to the end;
> - the installer's edits were applied to fresh clones of the two pinned
>   Pi-Star repositories: the patch in `patches/` applies, the sed edits
>   find exactly the lines they expect, the edited upstream bash scripts
>   still pass `bash -n`;
> - the sudoers file the installer extracts passes `visudo -c -f`;
> - `board/pistar-b96-presets` was run against Pi-Star's default
>   `mmdvmhost` file;
> - the installer's file helpers (install / keep / move aside / manifest)
>   and the uninstaller's remove-and-restore loop were run on a scratch
>   directory, with ownership changes stubbed out.
>
> The temporary upstream clones used for this were deleted afterwards.
>
> **`php -l` was not run** on the patched PHP files: there was no PHP
> interpreter. The patch adds one `if` block (a single `shell_exec` call)
> to one file.
>
> The assumptions are listed in "Assumptions" below. Expect to debug.

## Licence situation

GitHub shows **no licence** for `AndyTaylorTweet/Pi-Star_DV_Dash`,
`Pi-Star_Binaries_sbin` and `Pi-Star_v43_Binaries_Bin`. Therefore:

- **Nothing of Pi-Star is in this repository.** No dashboard file, no
  script, no configuration file, no firmware.
- `install-pistar.sh` downloads them from upstream onto your board, at the
  commits in `pins.conf`, and edits them there. The edits are a handful of
  `sed` commands in the installer (each with its reason) and one unified
  diff in `patches/`.
- The files in `board/` are this repository's own replacements for Pi-Star
  scripts that cannot work here. They keep the upstream file *names* (the
  dashboard calls them by name) and nothing else.
- The radio programs (g4klx, juribeparada, on7lds; GPL) are built from
  their sources on the board.

Pi-Star is the work of Andy Taylor (MW0MWZ) and contributors:
<https://www.pistar.uk/>. This is not a Pi-Star release and is not supported
by the Pi-Star project; do not take problems with it to the Pi-Star
support group.

## This package or the minimal one: choose one

`software/bubblegum96/` has two radio stacks for the same modem:

| | Minimal package (`../mmdvm`) | Pi-Star (this directory) |
|---|---|---|
| MMDVM host | current `MMDVM-Host` (MQTT) | `MMDVMHost` of 2025-09-25 (log files, built-in Nextion driver, direct DMR master login) |
| Display | `MMDVM-Display` | MMDVMHost itself, `Port=modem` |
| BrandMeister | through DMRGateway, `setup-brandmeister.sh` | MMDVMHost direct, set in the web page |
| Configuration | edit ini files | web pages |
| Files | `/etc/MMDVM-Host.ini`, `/etc/DMRGateway.ini` | `/etc/mmdvmhost`, `/etc/dmrgateway`, ... |

They cannot run together: both use `/dev/ttyOWL2` and both define
`mmdvmhost.service`, `dmrgateway.service` and `ysfgateway.service`.

- `install-pistar.sh` **refuses to run** while one of the minimal package's
  units is enabled or active, and tells you what to disable.
- If the minimal package is installed but switched off, its three unit
  files and its `DMRGateway` / `YSFGateway` binaries are moved to
  `/var/lib/pistar-b96/displaced/` and `uninstall-pistar.sh` puts them back.
  `/etc/MMDVM-Host.ini`, `/etc/DMRGateway.ini`, `MMDVM-Host`,
  `MMDVM-Display` and mosquitto are not touched.
- Running `../install.sh` again later re-creates the minimal package's
  `mmdvmhost.service` in `/etc/systemd/system`, which shadows Pi-Star's; run
  `install-pistar.sh` once more afterwards (it moves the file aside again).
- The **board files** of `../install.sh` are needed by both: device tree,
  `mmdvm-gpio` + `mmdvm-gpio-init.service`, `flash-mmdvm-hs`, fan, battery,
  gpsd / chrony, network. Install them first. Pi-Star here calls
  `mmdvm-gpio` and `flash-mmdvm-hs`.

## Installation

1. Kernel, device tree and board files as in `../README.md`, steps 1-3, 5,
   6 and 9 (not the MMDVM build, not `enable ... mmdvmhost`). Check that
   `/dev/ttyOWL2` exists.
2. Copy this directory to the board with its scripts intact (LF line
   endings; `.gitattributes` here takes care of that for git checkouts).
3. Look at what it will do:

       bash install-pistar.sh --dry-run

4. Install (network needed; the build takes a while on four Cortex-A53):

       sudo bash install-pistar.sh

   It asks once for the web admin password (no echo). Press Enter to start
   with Pi-Star's default instead.

   Options: `--no-gpsd` (gateways without gpsd), `--with-dstar` (also build
   ircDDBGateway; see FEATURES.md), `--with-firewall` (run Pi-Star's
   iptables script at every boot), `--hostname pi-star`, `--skip-apt`,
   `--skip-build`.
5. Reboot.
6. Flash the modem if it is blank: `sudo flash-mmdvm-hs <firmware.bin>`.
7. Browse to `http://<board address>/` and follow
   `configure-brandmeister.md`.

Running the installer again is safe: it replaces only files it installed
itself, keeps every existing configuration file, and rebuilds a program
only when its pin changed. To move to newer upstream versions change
`pins.conf` and run it again - then also re-check that the edits still
apply (the installer stops if they do not).

Remove: `sudo bash uninstall-pistar.sh` (keeps your configuration) or
`... --purge`. `--dry-run` is accepted there too.

## Web login

- Address: `http://<board address>/`; the admin pages are under `/admin/`.
- User: **`pi-star`**.
- Password: what you typed when the installer asked. If you pressed Enter
  (or the installer had no terminal): Pi-Star's well-known default,
  **`raspberry`**.
- **Change it** on the Configuration page, last section ("Remote Access
  Password"). With the default password the dashboard shows a red banner,
  and sends clients from outside the board's own subnets to a page that
  only lets them set a new password. The dashboard rejects `raspberry` as a
  new password.
- The same action sets the Linux password of the account `pi-star`. That
  account is created here only for this purpose and has no login shell.
- The connection is plain HTTP, as on Pi-Star.

## Security: what the web password is worth

The dashboard changes the system through `sudo`. The installer gives
`www-data` the command allowlist that Pi-Star itself uses since 4.3.x
(`/etc/sudoers.d/pistar-dashboard`, extracted from the pinned
`pistar-upgrade`, minus the read-only remount), plus one command of its own
(`/etc/sudoers.d/pistar-b96`). It never adds `NOPASSWD: ALL`.

That allowlist still includes rewriting `/etc/crontab`, installing files
into `/etc`, changing a password with `chpasswd`, reboot and shutdown.
**Anyone who knows the web admin password controls the machine as root**,
and so does anything that can run commands as `www-data`. Passwords for the
DMR networks are stored in clear text in world-readable files
(`/etc/mmdvmhost`), as on every Pi-Star. Treat the board like a Pi-Star:
keep it on a trusted LAN, do not forward port 80 to it.

Ports: the installer opens none and installs no firewall rules unless you
pass `--with-firewall`, which runs Pi-Star's own `pistar-firewall`
unchanged. uPnP port mapping is off until you switch it on in the
dashboard.

## What the installer changes on the system

| Where | What |
|---|---|
| packages | nginx, php-fpm (+ cli, mbstring, zip), apache2-utils, git, build-essential, zip / unzip, psmisc, netcat-openbsd, net-tools, wireless-tools, iw, wpasupplicant, miniupnpc, iptables, stm32flash, gpsd + libgps-dev (libwxgtk3.2-dev with `--with-dstar`) |
| `/var/www/dashboard` | dashboard, git checkout at the pin, edited |
| `/opt/pistar-b96/src` | the other source trees |
| `/usr/local/sbin` | Pi-Star scripts and wrappers, the replacements from `board/` |
| `/usr/local/bin` | `MMDVMHost`, `RemoteCommand`, gateways, parrots, cross-mode programs, `MMDVMCal`, `NextionDriver`, `platformDetect.sh`, `config_clean.zip`, `firmware/hs_dual_hat.bin` |
| `/usr/local/etc` | `RSSI.dat`, audio prompts, host / ID files, `pistar-b96-pins` |
| `/etc` | `mmdvmhost`, `dmrgateway`, ... (Pi-Star defaults, only if absent), `pistar-release`, `sudoers.d/pistar-dashboard`, `sudoers.d/pistar-b96`, `cron.d/pistar-b96`, `logrotate.d/pistar-b96`, `udev/rules.d/99-pistar-b96-modem.rules`, `nginx/sites-available/pi-star`, `php/<ver>/fpm/conf.d/99-pistar-hardening.ini`, `netplan/61-pistar-b96-wlan.yaml`, `wpa_supplicant/wpa_supplicant.conf`, one commented line in `/etc/crontab` |
| `/lib/systemd/system` | `<name>.service` + `<name>.timer` for every Pi-Star daemon, `nextiondriver`, `pistar-watchdog`, `pistar-upnp` (disabled), `pistar-b96-wifi.path` / `.service` |
| `/lib/crda/db.txt` | country codes for the Wi-Fi page |
| `/var/www/.htpasswd` | hash of the admin password, mode 600 `www-data` |
| `/var/log/pi-star` | logs, `root:mmdvm` 775 |
| users | `mmdvm` (if missing), `pi-star` (no login shell) |
| moved aside | nginx's `sites-enabled/default`; units and binaries of the minimal package |
| `/var/lib/pistar-b96` | manifest of all of the above, displaced originals, build stamps |

Board adaptations, each a commented function in `install-pistar.sh`:

| Adaptation | Function | How |
|---|---|---|
| Read-only root (`rpi-rw` / `rpi-ro`, `mount -o remount,ro`) | `neutralise_remount_ro`, `board/rpi-rw`, `board/rpi-ro` | every `remount,ro` in dashboard and scripts becomes `true`; the two commands are no-ops |
| Modem port | `adapt_modem_port`, `board/pistar-b96-presets` | udev: `/dev/ttyAMA0` -> `ttyOWL2`, group `mmdvm` |
| Platform string | `board/platformDetect.sh` | device-tree model |
| CPU temperature | `adapt_dashboard` (2), `board/pistar-b96-temp` | `thermal_zone0`, else TMP102 |
| Wi-Fi | `adapt_wifi` | `wpa_supplicant@wlan0` on Pi-Star's file, netplan DHCP, reload path unit |
| Modem firmware flash | `board/pistar-modemupgrade` | wrapper around `flash-mmdvm-hs` |
| Modem reset / detection | `board/pistar-mmdvmhshatreset`, `board/pistar-findmodem` | `mmdvm-gpio`; no probing |
| Display | `board/pistar-b96-presets` | `Port=modem`, `ScreenLayout=3` |
| GPS | `build_radio` (`USE_GPSD`), presets | gateways talk to gpsd; MobileGPS not used |
| Update / upgrade / factory reset | `board/pistar-update`, `-upgrade`, `-factory-reset` | no git pull, no apt |
| Watchdog | `board/pistar-watchdog` | bash instead of Python 2 |
| Daily job | `cron_and_logs`, `board/pistar-b96-daily` | host files, log clean-up |
| Firewall | `adapt_firewall` | only with `--with-firewall` |
| Host name | `adapt_hostname` | only with `--hostname` |
| Restore page | `patches/dashboard/0001-...` | board presets after a restore |

## Assumptions

Every one of these is unverified. They are ordered by how likely they are
to stop a first boot from working.

**Web**

1. The dashboard at the pin runs under PHP 8.3 (Pi-Star 4.3 uses the PHP of
   its Debian base, presumably 8.2).
2. `sudo` works from php-fpm on Ubuntu 24.04 (no `NoNewPrivileges`, no
   sandboxing in the `php8.3-fpm` unit), and php-fpm's `/tmp` is the same
   `/tmp` the sudo'd commands see.
3. Pi-Star's sudoers allowlist names commands as `/bin/...`, `/sbin/...`;
   on Ubuntu those directories are symlinks into `/usr`. sudo is assumed to
   match them (it compares the files, not only the path strings) as it must
   on Pi-Star's own merged-`/usr` Debian.
4. The allowlist at the sbin pin covers every sudo call of the dashboard at
   the dash pin (both are upstream HEAD of the same day).
5. The nginx site here is written from scratch; Pi-Star's own is not
   published. `snippets/fastcgi-php.conf` and
   `/run/php/php<ver>-fpm.sock` are Ubuntu's names.
6. HTTP basic-auth credentials reach PHP (`PHP_AUTH_PW`), which the
   default-password check needs.

**Radio programs**

7. All pinned sources compile with Ubuntu 24.04's GCC 13 on arm64, and the
   gateways with its libgps. Nothing was compiled. If a `USE_GPSD` build
   fails, use `--no-gpsd`.
8. MMDVMHost's plain `Makefile` (no OLED / HD44780 / WiringPi) is the right
   one. Pi-Star's binary is linked against WiringPi and ArduiPi_OLED.
9. MMDVMCal, the MMDVM_CM programs, NextionDriver and ircDDBGateway are
   built from *inferred* commits (`pins.conf`).
10. Passing `CFLAGS=` / `LIBS=` on the make command line selects the gpsd
    variant of the gateway Makefiles without side effects.
11. `--with-dstar`: g4klx/ircDDBGateway builds against wxWidgets 3.2, the
    binaries end up at the paths the installer copies from, and the
    `LOGDIR` / `CONFDIR` / `DATADIR` chosen match what the dashboard reads.

**Services**

12. The systemd units are generated after the pattern visible in
    `pistar-upgrade`; the real ones are not published. A `Type=forking`
    unit whose wrapper exits 0 without starting anything is assumed to end
    up inactive without an error.
13. MMDVMHost with `Daemon=1` switches to user `mmdvm` with that user's
    primary group only; the udev rule gives that group the modem port.
    Whether the Pi-Star image does it this way is not known.
14. `/dev/ttyAMA0` does not exist as a real device on the S900 kernel, so
    the alias is free. (The installer stops if it does.)
15. A udev `SYMLINK` on a tty is enough for MMDVMHost, MMDVMCal and
    `stm32flash`.
16. `mmdvm-gpio-init.service` has put BOOT0 / NRST in their idle state
    before `mmdvmhost.timer` fires (30 s after boot).
17. The replacement watchdog's process name is what the admin page's
    `pgrep -f /usr/local/sbin/pistar-watchdog` looks for.

**Modem and display**

18. Pi-Star's `hs_dual_hat.bin` suits this board: host on USART1, serial
    repeater on USART2 enabled, repeater baud rate equal to the TJC
    screen's `bauds=`. The file was not examined. `stm32flash` success is
    detected by exit code only.
19. `ScreenLayout=3` of the old built-in Nextion driver sends the fields the
    screen file of `display/tjc8048x550` (drawn for MMDVM-Display, layout 3)
    expects. Checked afterwards by comparing the command strings of the two
    `Nextion.cpp` sources: the old driver uses no page or object that the
    layout lacks. Still not seen on a display.
20. `UARTSpeed=115200` is the firmware's host speed.

**Network and data**

21. `www.pistar.uk` serves the host / ID files to this system. Without them
    the DMR master list on the configuration page is empty.
22. Wi-Fi: the interface is, or can be renamed to, `wlan0`; netplan accepts
    a Wi-Fi interface listed under `ethernets` with the networkd renderer;
    `wpa_supplicant@wlan0.service` and the `netdev` group exist; `ifconfig`
    / `iwconfig` output is what the page parses. The on-board Wi-Fi of the
    Bubblegum-96 needs a driver your kernel may not have.
23. `--with-firewall`: Pi-Star's rule set (OUTPUT policy DROP) does not
    block something this board needs (gpsd is local; chrony / NTP, apt and
    the Meshtastic tools were not checked against the list).
24. The sample ini files used for M17Gateway, DAPNETGateway and APRSGateway
    (Pi-Star's own are not published) have the keys the configuration page
    expects.

**Other**

25. `/sys/class/thermal/thermal_zone0` is probably absent; then the "CPU
    Temp" on the dashboard is the TMP102 at the fan outlet.
26. `nc -ulp` in `pistar-calibration-start` works with `netcat-openbsd`.
27. The dashboard's host-name field: `/etc/hosts` contains the current host
    name, and nothing (cloud-init) resets `/etc/hostname` at boot.
28. Restoring a backup from a Raspberry Pi Pi-Star works apart from the
    keys the patch rewrites.

## When something does not work: look here first

1. **nginx error log** - `sudo tail -50 /var/log/nginx/error.log`. PHP
   errors and the stderr of every failed `sudo` call end up here. A blank
   or half-drawn page is almost always a PHP error.
2. **sudo** - `sudo -l -U www-data` must list `PISTAR_DASH_ALL`.
   `journalctl -t sudo -n 50` shows commands that were refused ("command
   not allowed") - that is a gap in the allowlist, or a path that does not
   match. `sudo visudo -c` checks the files.
3. **Unit names** - `systemctl list-unit-files 'mmdvmhost*' 'dmrgateway*'
   'pistar-*'`. `systemctl cat mmdvmhost.service` must show the unit from
   `/lib/systemd/system` with `ExecStart=/usr/local/sbin/mmdvmhost.service
   start`; if it shows `/etc/systemd/system/mmdvmhost.service` with
   `MMDVM-Host`, the minimal package's unit is shadowing it.
4. **Why a daemon does not start** - run the wrapper by hand:
   `sudo /usr/local/sbin/mmdvmhost.service start; echo $?`, then
   `sudo /usr/local/bin/MMDVMHost /etc/mmdvmhost` in the foreground after
   setting `Daemon=0`. The wrappers exit silently when the callsign is
   still `M1ABC`, the ID `1234567`, or no modem type has been applied.
5. **Log path** - the dashboard reads `/var/log/pi-star/MMDVM-<UTC
   date>.log`. `ls -l /var/log/pi-star` (must be `root:mmdvm`, 775);
   `[Log] FilePath=/var/log/pi-star`, `FileRoot=MMDVM`, `FileLevel` not 0
   in `/etc/mmdvmhost`. No file = MMDVMHost is not running or cannot write.
6. **Modem port** - `ls -l /dev/ttyOWL2 /dev/ttyAMA0`: the second must be a
   symlink to the first, the first `root:mmdvm` `crw-rw----`.
   `sudo pistar-findmodem` prints both.
7. **PHP service** - `systemctl status php8.3-fpm nginx`;
   `sudo nginx -t`.
8. **What the installer did** - `/var/lib/pistar-b96/manifest`,
   `manifest-conf`, `displaced/`.

## Files

| File | Purpose |
|---|---|
| `install-pistar.sh` | the installer (`--dry-run`, options above) |
| `uninstall-pistar.sh` | removes what the installer recorded (`--purge`, `--dry-run`) |
| `pins.conf` | pinned repositories and commits, and how each was chosen |
| `patches/dashboard/*.patch` | unified diffs against the pinned dashboard, applied with `git apply`; the installer stops if one does not apply. (`patches/sbin/` would be applied to the scripts; there is none) |
| `board/` | replacements for Pi-Star scripts that cannot work on this board, and helpers |
| `RESEARCH.md` | what a Pi-Star system consists of, with upstream file and line |
| `FEATURES.md` | every Pi-Star function and its status on this board |
| `configure-brandmeister.md` | first configuration for DMR on BrandMeister |
