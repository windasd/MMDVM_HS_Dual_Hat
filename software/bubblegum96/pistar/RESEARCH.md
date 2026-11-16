# What a Pi-Star system consists of

Read from the upstream repositories on 2026-11-16, at the commits pinned in
`pins.conf`. File names and line numbers refer to those commits:

| Short name | Repository | Commit |
|---|---|---|
| dash | `AndyTaylorTweet/Pi-Star_DV_Dash` | `ca50804e` (2026-10-22, `config/version.php`: 20261008) |
| sbin | `AndyTaylorTweet/Pi-Star_Binaries_sbin` | `3c736123` (2026-10-22) |
| bin | `AndyTaylorTweet/Pi-Star_v43_Binaries_Bin` | `f851131d` (2025-09-25) |

Nothing here was observed on a running Pi-Star; no Pi-Star image was
unpacked. Where a fact is only present in the image (and therefore not in any
repository) it is marked **image-only** and what is written about it is an
inference from the scripts that refer to it.

GitHub shows no licence for the three Pi-Star repositories. Nothing from
them is copied into this repository; file names, paths, option names and the
behaviour of the scripts are described, their text is not reproduced.

## 1. The pieces

- **Dashboard** (dash): PHP pages in `/var/www/dashboard`, a git checkout
  that `pistar-update` pulls. It never talks to the radio programs
  directly: it parses their **log files** and edits their **ini files**.
- **Management scripts** (sbin): a git checkout that *is* `/usr/local/sbin`
  (`sbin:pistar-update:176`, `git_update /usr/local/sbin`).
- **Programs** (bin): a git checkout that *is* `/usr/local/bin`: prebuilt
  radio programs, `platformDetect.sh`, `config_clean.zip`, `firmware/`,
  `Nextion/`, and wrapper scripts `apt`, `apt-get`, `aptitude`, `dpkg` that
  remount the root file system read-write before calling the real tool.
- **The image**: Raspberry Pi OS with a read-only root, nginx, php-fpm,
  systemd unit files, `/etc/rc.local`, `/etc/crontab` entries, tmpfs mounts,
  users. **image-only.**

## 2. Radio software: sources, versions, binaries

### 2.1 The prebuilt binaries cannot be used

`file` on `bin:MMDVMHost` and `bin:DMRGateway`: *ELF 32-bit LSB executable,
ARM, EABI5, dynamically linked, interpreter /lib/ld-linux-armhf.so.3*. Dynamic
dependencies (from the strings in the files):

| Binary | Needs besides libc / libstdc++ |
|---|---|
| `MMDVMHost`, `RemoteCommand` | `libwiringPi.so`, `libwiringPiDev.so`, `libArduiPi_OLED.so.1` |
| `dstarrepeaterd` | `libwiringPi.so`, `libwx_baseu-3.0`, `libasound`, `libusb-1.0` |
| `ircddbgatewayd`, `timeserverd` | `libwx_baseu-3.0`, `libwx_baseu_net-3.0` |
| gateways, parrots, cross-mode programs | nothing else |

Highest glibc symbol version referenced: 2.28. On Ubuntu 24.04 **arm64** they
would need the armhf architecture added (multiarch), a kernel with
`CONFIG_COMPAT`, an armhf WiringPi and ArduiPi_OLED, and wxWidgets 3.0, which
Ubuntu 24.04 does not have. Everything is therefore built from source.

### 2.2 Which source the binaries were built from

The g4klx programs print `Built ... (GitID #xxxxxxx)`; the full 40-digit id is
in the binary. Extracted with `grep -a` from the files at bin `f851131d`, then
looked up in the g4klx repositories (all are on the default branch):

| Program(s) | Version string in the Pi-Star binary | Embedded commit | Repository, commit date |
|---|---|---|---|
| MMDVMHost | `20250925_PS4` | `05b10ac5` | `g4klx/MMDVM-Host` (formerly `MMDVMHost`), 2025-09-25, "Merge pull request #849 from MW0MWZ/master" |
| DMRGateway | `20250318_PS4` | `ec5c32b5` | `g4klx/DMRGateway`, 2025-03-15 |
| YSFGateway | `20250616_PS4` | `598854b2` | `g4klx/YSFClients`, 2025-06-15 |
| YSFParrot, DGIdGateway | `20250521_PS4` | `75c84508` | `g4klx/YSFClients`, 2025-05-21 |
| P25Gateway, P25Parrot | `20250405_PS4` | `298b9b4d` | `g4klx/P25Clients`, 2025-04-04 |
| NXDNGateway, NXDNParrot | `20250320_PS4` | `5e235f73` | `g4klx/NXDNClients`, 2025-03-19 |
| DAPNETGateway | `20250408_PS4` | `dde4c01a` | `g4klx/DAPNETGateway`, 2025-03-18 |
| APRSGateway | `20240130_PS4` | `7fd8ad32` | `g4klx/APRSGateway`, 2024-01-29 |
| M17Gateway | `20250318_PS4` | `2be36e45` | `g4klx/M17Gateway`, 2025-03-17 |

The `_PS4` suffix and the date are not in upstream's `Version.h` (MMDVMHost at
`05b10ac5` says `20250828`): Pi-Star changes the version string when building.
Whether it changes anything else is not known. A source built here will
report upstream's string, so the versions on the dashboard's "SysInfo" page
will differ from a real Pi-Star in exactly that respect.

MMDVMHost at `05b10ac5` is the pre-MQTT program the dashboard needs:
`MMDVM.ini` has `[Log] FilePath / FileRoot / FileLevel / FileRotate`,
`[DMR Network] Type=Direct|Gateway` with `RemoteAddress` and `Password`, the
built-in `[Nextion]` section with `Port=modem`, and the Makefile lists
`Nextion.o`, `DMRDirectNetwork.o`, `Log.o`; there is no MQTT source file.

No commit id is embedded in these; the pins are inferred (see `pins.conf`):

| Program(s) | Evidence | Pin |
|---|---|---|
| YSF2DMR, YSF2NXDN, YSF2P25, DMR2YSF, DMR2NXDN, NXDN2DMR | version `20240908_PS4`; `juribeparada/MMDVM_CM` has had no commit since 2024-09-07 | `7328c9e9` (HEAD) |
| MMDVMCal | binary last updated by bin commit `bedf7f2` (2025-04-16) | `f530cc9f` (2024-01-12), newest before that |
| NextionDriver | binary last updated by bin commit `7ff54f4` (2025-04-11) | `on7lds/NextionDriver` `1437e4e2` (2024-12-24) |
| ircddbgatewayd, remotecontrold, timeserverd, starnetserverd | wx 3.0 binaries, no version found | `g4klx/ircDDBGateway` `6680e4b7` (2025-04-27), the last commit before the MQTT branch was merged (2026-02-18) |
| dstarrepeaterd | needs WiringPi; only for non-MMDVM modems | not built |
| MobileGPS | version `20200517_Pi-Star` | not built (section 6.9) |
| AMBEserver, timercontrold, text/voice/aprs transmit tools | - | not built |

## 3. Directory layout

| Path | Content | Source |
|---|---|---|
| `/etc/mmdvmhost` | MMDVMHost ini (a *file*, not a directory) | `dash:config/config.php:24-25` (`MMDVMINIPATH` `/etc`, name `mmdvmhost`), `sbin:mmdvmhost.service:16` |
| `/etc/dmrgateway`, `ysfgateway`, `p25gateway`, `nxdngateway`, `m17gateway`, `dgidgateway`, `dapnetgateway`, `aprsgateway`, `ysf2dmr`, `ysf2nxdn`, `ysf2p25`, `dmr2ysf`, `dmr2nxdn`, `nxdn2dmr`, `mobilegps` | one ini file per program | `CONFIG=` in each `sbin:*.service`; `dash:admin/configure.php:120-200` |
| `/etc/ircddbgateway`, `/etc/dstarrepeater`, `/etc/timeserver`, `/etc/starnetserver` | flat `key=value` files of the D-Star programs | `dash:config/ircddblocal.php:22-27` |
| `/etc/dstar-radio.mmdvmhost` or `/etc/dstar-radio.dstarrepeater` | marker + `[Modem] Hardware=<id>`: which controller software is in use. Without one the system is "unconfigured" and no radio service starts | `sbin:mmdvmhost.service:30-46`, `dash:admin/configure.php:215-218` |
| `/etc/pistar-release` | ini: `[Pi-Star]`, `Version = x.y.z`, `Hardware = RPi` ... | `dash:index.php:93`, `sbin:pistar-upgrade:279-281` |
| `/etc/pistar-css.ini` | dashboard colours (CSS tool) | `dash:index.php` |
| `/etc/pistar-remote`, `/etc/pistar-keeper` | settings of two Python programs | `sbin:pistar-watchdog`, `sbin:pistar-keeper` |
| `/etc/bmapi.key`, `/etc/dapnetapi.key`, `/etc/tgifapi.key` | API keys, mode 600 `www-data` | `dash:mmdvmhost/bm_manager.php:38`, `sbin:pistar-upgrade:86-88` |
| `/etc/hostfiles.nodextra`, `/etc/timeserver.dissable`, `/etc/hostap.off` | flag files | `sbin:pistar-upgrade:151-161` |
| `/usr/local/bin` | radio programs, `RemoteCommand`, `platformDetect.sh`, `config_clean.zip`, `firmware/` | bin; `dash:config/config.php:26` |
| `/usr/local/sbin` | all scripts of sbin | sbin |
| `/usr/local/etc` | `DMRIds.dat`, `NXDN.csv`, `*_Hosts.txt` / `*Hosts.txt`, `TGList_*.txt`, `XLXHosts.txt`, `RSSI.dat`, `DMR_Audio/`, `P25_Audio/`, `nextionGroups.txt`, `nextionUsers.csv` | `sbin:HostFilesUpdate.sh`, `bin:config_clean.zip` (paths inside `mmdvmhost`, `dmrgateway`) |
| `/var/log/pi-star` | `MMDVM-YYYY-MM-DD.log`, `DMRGateway-...`, `YSFGateway-...`, `P25Gateway-...`, `Links.log`, `Headers.log`, `pi-star_update.log`, `pi-star_upgrade.log`, `pi-star_modemflash.log`, `pi-star_icmptest.log`; owner `root:mmdvm`, mode 775 | `dash:config/config.php:22-43`, `sbin:mmdvmhost.service:54-59`, `dash:admin/update.php:50-52` |
| `/var/www/dashboard` | document root | `sbin:pistar-update:193`, `sbin:pistar-upgrade:405` |
| `/var/www/.htpasswd` | basic-auth file, user `pi-star` | `dash:admin/configure.php:448` |
| `/root/ipv4.fw`, `/root/ipv6.fw`, `/root/DMR_Hosts.txt`, `/root/YSFHosts.txt`, `/root/P25Hosts.txt` ... | user additions that survive updates | `sbin:pistar-firewall`, `sbin:HostFilesUpdate.sh` |
| `/tmp` | staging area: the dashboard writes a new file as `www-data` and installs it with `sudo install` | `dash:config/config_writer.php:320-346` |

`bin:config_clean.zip` holds the factory defaults of 16 of these files
(`dgidgateway dmr2nxdn dmr2ysf dmrgateway dstarrepeater ircddbgateway
mmdvmhost nxdngateway p25gateway pistar-remote starnetserver timeserver
ysf2dmr ysf2nxdn ysf2p25 ysfgateway`), dated 2018-2021; the configuration
page adds newer sections to them when it saves. There is none for
`m17gateway`, `dapnetgateway`, `aprsgateway`, `nxdn2dmr`, `mobilegps`
(**image-only**, or downloaded on demand: `sbin:mobilegps.service` fetches
`MobileGPS.ini` from GitHub).

## 4. Services

Each radio program has a **wrapper script** `sbin:<name>.service` - a
start/stop/restart/status shell script, not a systemd unit - which decides
whether the program should run at all: it exits quietly when the binary or
the ini file is missing, when the system is unconfigured, when the placeholder
callsign `M1ABC` / id `1234567` is still in the file, or when the mode is
switched off in `/etc/mmdvmhost` (`sbin:dmrgateway.service:27-41`,
`sbin:mmdvmhost.service:26-52`). `dmrgateway.service` additionally starts
only when `[DMR Network] Address=127.0.0.1`, i.e. when "DMRGateway" was chosen
as the DMR master; with a BrandMeister master chosen directly, MMDVMHost logs
in itself and DMRGateway does not run.

The systemd units that call the wrappers are **image-only**, but
`sbin:pistar-upgrade` creates several of them, which shows the pattern
(lines 330-341 mobilegps, 467-485 aprsgateway, 529-541 pistar-upnp, 563-580
dgidgateway, 687-706 m17gateway, 928-943 nextiondriver): `Type=forking`,
`ExecStart=/usr/local/sbin/<name>.service start`, `ExecStop=... stop`,
`ExecReload=... restart`, `WantedBy=multi-user.target`, plus `<name>.timer`
with `OnStartupSec=20`; the *timer* is enabled. They live in
`/lib/systemd/system` (the dashboard edits
`/lib/systemd/system/mmdvmhost.timer` and `dstarrepeater.timer` with sed,
`dash:admin/configure.php:1786-1787`).

Unit names used by the dashboard and the scripts (`dash:admin/configure.php:
551-576`, `sbin:pistar-update:106-135`, `sbin:pistar-upgrade:50-76`):
`mmdvmhost dstarrepeater ircddbgateway timeserver starnetserver dmrgateway
ysfgateway ysfparrot dgidgateway p25gateway p25parrot nxdngateway nxdnparrot
m17gateway dapnetgateway aprsgateway ysf2dmr ysf2nxdn ysf2p25 dmr2ysf dmr2nxdn
nxdn2dmr mobilegps nextiondriver pistar-watchdog pistar-remote pistar-upnp
pistar-keeper pistar-ap cron`, and the timers `mmdvmhost.timer`,
`pistar-watchdog.timer`, `pistar-upnp.timer`.

The dashboard decides "running / not running" with `pgrep <program name>`
(`dash:admin/admin.php:52-57`, `dash:mmdvmhost/tools.php:75-80`), not with
systemd.

The radio programs run with `Daemon=1`: they fork and switch to user
`mmdvm` (`getpwnam("mmdvm")`, `setgid`, `setuid`; `MMDVMHost.cpp:207-250` at
the pinned commit). No supplementary groups are set, so that user's primary
group must be able to open the modem port and write `/var/log/pi-star`. How
the Pi-Star image arranges the former is **image-only**.

## 5. Web server, PHP, authentication

- **nginx**, site file `/etc/nginx/sites-available/pi-star`
  (`sbin:pistar-upgrade:803`), `listen 80 default_server` and, since 4.1.10 /
  4.2.3, `listen [::]:80 default_server` (lines 804-806). PHP is handled by an
  included `/etc/nginx/default.d/php.conf` (line 417, in the captive-portal
  site that the same script writes). That captive-portal block also shows the
  admin location: `location ^~ /admin { ... client_max_body_size 512K; ... }`
  and `location ~ /\.git { deny all; }` (lines 409-422). The `pi-star` site
  file itself is **image-only**.
- **php-fpm**; the version is whatever the image's Debian release has.
  `sbin:pistar-upgrade:1287-1295` loops over `/etc/php/*/fpm` and writes
  `conf.d/99-pistar-hardening.ini` (`session.upload_progress.enabled = 0`).
  PHP extensions the dashboard calls: `mbstring` (`mb_strimwidth`), `zip`
  (`ZipArchive` in `admin/config_backup.php`), `json`.
- **Document root** `/var/www/dashboard`; every page uses
  `$_SERVER['DOCUMENT_ROOT']`.
- **Authentication**: HTTP basic auth for `/admin`, file
  `/var/www/.htpasswd`, user `pi-star`. The dashboard changes the password
  with `htpasswd -i /var/www/.htpasswd pi-star` (run as `www-data`, no sudo)
  and at the same time the Linux password of user `pi-star` with
  `sudo -n /usr/sbin/chpasswd` (`dash:admin/configure.php:428-475`,
  `dash:admin/change_password_required.php:110-161`). The initial password is
  `raspberry`: `dash:config/banner_warnings.inc:132-139` compares the supplied
  basic-auth password with that string, shows a red banner, and redirects
  clients that are not in a local subnet to `change_password_required.php`
  (lines 277-318).
- **CSRF tokens and security headers**: `dash:config/csrf.php`,
  `dash:config/security_headers.php` (PHP sessions).
- **Public part**: `/` (live dashboard), `/api/` are not behind
  authentication.

## 6. sudo

Until Pi-Star 4.1.10 / early 4.3.x, `/etc/sudoers` contained
`www-data ALL=(ALL) NOPASSWD: ALL`. `sbin:pistar-upgrade:24-264`
(`deploy_sudoers_tightening`) replaces it with
`/etc/sudoers.d/pistar-dashboard`: 16 command aliases
(`PISTAR_DASH_SYSTEMCTL`, `_MOUNT`, `_INSTALL`, `_CP_STAGE`, `_STAGE_PERMS`,
`_LOGS`, `_MARKERS`, `_SED`, `_READ_PRIV`, `_PASSWD`, `_NETWORK`, `_TIME`,
`_POWER`, `_BACKUP`, `_MISC`, `_SCRIPTS`) and
`www-data ALL=(root) NOPASSWD: PISTAR_DASH_ALL`. It is validated with
`visudo -c` before and after installation. The comments at lines 815-890
describe three rounds of additions "driven by an empirical sudo -ln probe of
every distinct command pattern in the dashboard".

What the dashboard runs through sudo (tally over dash, `grep -o "sudo ..."`):
`mount -o remount,rw|ro /` (73), `install -m ... /tmp/x <target>` (51),
`sed -i` (30), `systemctl start|stop|restart` (72), `cp <config> /tmp/x`,
`chown www-data:www-data`, `chmod 600` (19 each), `sync`,
`/usr/local/bin/RemoteCommand`, `remotecontrold`, `rm -rf`, `truncate -s 0`,
`timedatectl set-timezone`, `reboot`, `shutdown -h now`, `zip -j`,
`wpa_cli`, `ip link`, `ifup` / `ifdown`, `chpasswd`, `touch`, `mkdir`,
`cat` / `grep` of the Wi-Fi file, and the scripts `pistar-update`,
`pistar-upgrade`, `pistar-modemupgrade`, `pistar-jittertest`,
`pistar-calibration-start`, `pistar-factory-reset --really`.

The allowlist is not a security boundary against someone who knows the admin
password: it permits, among others, `sed -i <anything> /etc/crontab`,
`install ... /tmp/* /etc/hosts`, `chpasswd` and `zip *`.

## 7. Cron, timers, updates

- `sbin:pistar-daily.cron` (189 lines): `HostFilesUpdate.sh`; `git pull` of
  the dashboard, `/usr/local/bin` and `/usr/local/sbin` with all services
  stopped; deletes `/var/log/pi-star/*.log` older than a day and every
  `*.gz` under `/var/log` older than a day; config migrations; installs
  `wiringpi_3.14_armhf.deb` from GitHub if WiringPi is older (lines 116-144);
  adds an `ExecStartPre=mkdir /var/log/nginx` to `nginx.service` (the log
  directory is on tmpfs).
- `sbin:pistar-hourly.cron`: truncates the nginx error log to 500 lines,
  `journalctl --vacuum-time=24h --vacuum-size=5M`, remounts `/` and `/boot`
  read-only.
- How the two are scheduled is **image-only** (`/etc/crontab` and
  `/etc/rc.local`, which shuffles the time of the daily jobs:
  `sbin:pistar-upgrade:449-452`).
- `sbin:pistar-update` (manual, and the dashboard's "Update" page): stops the
  services, `apt-get upgrade` when run from a terminal, `git pull` of the
  three trees (with a self-update and `git reset --hard origin/master` on
  failure), `HostFilesUpdate.sh`, `pistar-firewall`, config migrations,
  WiringPi, restarts the services, remounts read-only. Log:
  `/var/log/pi-star/pi-star_update.log` when not on a terminal.
- `sbin:pistar-upgrade`: a `case` over the version in `/etc/pistar-release`
  with one arm per release step (4.1.0 ... 4.1.13, 4.2.0 ... 4.2.6,
  4.3.0 ... 4.3.10); each arm edits image files and bumps the version. The
  last complete arm produces **4.3.10**; `dash:config/banner_warnings.inc`
  asks for an upgrade below 4.3.10.
- `sbin:HostFilesUpdate.sh`: downloads 17 lists plus two Nextion lists from
  `http://www.pistar.uk/downloads/` with `curl --user-agent
  "Pi-Star_<version>"` into `/usr/local/etc`, keeps one dated backup, appends
  the user's `/root/*Hosts.txt`, rewrites parts of `/etc/dmrgateway`.
- uPnP: `sbin:pistar-upnp.service` (a script calling `upnpc`) is run from an
  `/etc/crontab` line every 5 minutes and by `pistar-upnp.timer`; the
  dashboard comments / uncomments that line and individual port lines inside
  the script (`dash:admin/configure.php:2416-2448`, `5599-5660`).

## 8. Firewall and watchdogs

- `sbin:pistar-firewall` (389 lines): flushes all iptables / ip6tables
  tables, sets policy `DROP` for INPUT **and OUTPUT**, then an allow list
  (inbound: 22, 80, 443/tcp, 445/tcp and 137-139 from private networks, 5353,
  1900, DHCP, 10022/udp, 2460/udp, 20000/udp from private networks, the
  D-Star / YSF / P25 / NXDN / M17 UDP port ranges; outbound similarly),
  DSCP marking of the voice ports, optional `/root/ipv4.fw`, hostapd NAT when
  `/etc/hostapd/hostapd.conf` exists, and saves to `/etc/iptables.rules` /
  `/etc/ip6tables.rules`. What loads it at boot is **image-only**.
- `sbin:pistar-watchdog` (`#!/usr/bin/python`, Python 2: `import
  ConfigParser`): after 90 s, loops; `pgrep` for every radio program and
  `systemctl stop` / `start` of those not running (the wrapper then decides);
  when `/var/log` is over 90 % full it deletes rotated logs under `/var/log`
  and truncates logs. Started by `sbin:pistar-watchdog.service`
  (`/usr/bin/python /usr/local/sbin/pistar-watchdog`).
- `sbin:pistar-remote` (Python 2): RF remote control by special callsigns
  found in the logs. `sbin:pistar-keeper` (Python 2, `import bluetooth`).

## 9. Raspberry-Pi-specific places

### 9.1 Dashboard (dash)

| File:line | What | Handling here |
|---|---|---|
| 28 files, 73 x `sudo mount -o remount,rw /` / `remount,ro /`, e.g. `config/config_writer.php:411,560`, `admin/configure.php:3944`, `admin/power.php:107,113`, every `admin/expert/*.php` | read-only root | `remount,ro` -> `true` (installer); `remount,rw` left |
| `admin/configure.php:73`, `dstarrepeater/system.php:46` | `cat /sys/class/thermal/thermal_zone0/temp` | -> `pistar-b96-temp` |
| `admin/configure.php:345`, `dstarrepeater/system.php:65` | `/usr/local/bin/platformDetect.sh` | own script |
| `admin/configure.php:1815-2399` | about 60 x `$configmmdvm['Modem']['Port'] = "/dev/ttyAMA0"` (also `ttyACM0`, `ttyUSB0`, `ttyS2`, `ttySC0`) per modem type, copied to `UARTPort` | udev alias `/dev/ttyAMA0` |
| `admin/configure.php:2823` | `[TFT Serial] Port=/dev/ttyAMA0` | unused |
| `admin/configure.php:4252`, `5566` | port lists from `ls /dev | egrep "ttyA|ttyUSB"` | the alias appears as `ttyAMA0` |
| `admin/configure.php:4257,4360` | NanoPi `/dev/ttyS2` options | absent |
| `admin/configure.php:1797-1799` | Icom repeater: adds `eth0:1` to `/etc/network/interfaces` | not applicable (no such file) |
| `admin/configure.php:520-521`, `2674-2678`, `5637`; `config/config_writer.php:127` | `/etc/hostapd/hostapd.conf` (auto-AP SSID / PSK) | no hostapd: section hidden |
| `admin/configure.php:2655-2671` | host name via sed in `/etc/hostname`, `/etc/hosts` | unchanged |
| `admin/configure.php:5668-5673` | Wi-Fi iframe if `/sys/class/net/wlan0`, `wlan1` or `wlan0_ap` exists | interface named `wlan0` |
| `admin/wifi.php:75-262` | `ifconfig wlan0`, `iwconfig wlan0`, `iw dev wlan0 link` | packages `net-tools`, `wireless-tools`, `iw` |
| `admin/wifi.php:181,190,197` | `sudo ifdown wlan0` / `ifup wlan0` | line 197 -> `ip link`; 181 / 190 are behind commented-out buttons |
| `admin/wifi.php:244,266,446,466`, `admin/expert/fulledit_wpaconfig.php:66,83` | `/etc/wpa_supplicant/wpa_supplicant.conf` | same file, used by `wpa_supplicant@wlan0` |
| `admin/wifi.php:316-320` | country list from `/lib/crda/regulatory.bin` or `/lib/crda/db.txt`, else AU FR DE GB US JP | `db.txt` generated |
| `admin/wifi.php:470,478,480` | `ip link set wlan0`, `wpa_cli scan -i wlan0` | unchanged |
| `admin/config_backup.php:90,219-223` | backs up `/etc/dhcpcd.conf` when it has a static address | file absent: skipped by the page |
| `admin/expert/ssh_access.php:29-32` | `/etc/default/shellinabox` | absent: page says "not yet installed" |
| `admin/expert/modem_fw_upgrade.php:208-242` | names for Pi hat firmware ids | list comes from the replaced script |
| `config/banner_warnings.inc:349-362` | `Hardware == 'RPi'` old-version banner | `Hardware = Bubblegum96` |
| `admin/configure.php:337` | tooltip text "running on this Raspberry Pi" | cosmetic, unchanged |

No `vcgencmd`, `/boot`, `rpi-rw`, `raspi-config`, `/proc/cpuinfo` or WiringPi
call exists in the dashboard at this commit.

### 9.2 Scripts (sbin)

| File:line | What | Handling here |
|---|---|---|
| `pistar-update:58-62,153-157,353-357`, `pistar-upgrade:284-288,1374-1378`, `pistar-daily.cron:10-14`, `pistar-hourly.cron:18-22`, `pistar-expand`, `pistar-ap.service`, `pistar-factory-reset`, `pistar-mmdvmcal:27,55`, `pistar-mmdvmhost-module:116`, `mobilegps.service:41-45` | `mount -o remount,rw|ro /`, `/boot`, `/boot/firmware` | `remount,ro` -> `true` in the scripts that are installed |
| `pistar-update:301-336`, `pistar-daily.cron:116-144` | downloads and `dpkg -i` of `wiringpi_3.14_armhf.deb` | scripts replaced |
| `pistar-upgrade:348-360,975,1083-1096` | `/boot/config.txt`, `/boot/cmdline.txt`, `/boot/firmware/...` | script replaced |
| `pistar-upgrade:1346-1362` | `rpi-eeprom-update` on Pi 4 / 5 | script replaced |
| `pistar-findmodem:23-41`, `pistar-mmdvmhshatreset:62-80`, `pistar-modemupgrade:326-329,497-510` | sysfs GPIO `base + 20` / `+ 21` (Pi header BOOT0 / reset), found via `gpiochip*` names containing `0000.gpio`; if none matches the base is empty and the scripts export **global GPIO 20 and 21** | all three replaced |
| `pistar-modemupgrade:464-469,515-527` | WiringPi `gpio mode` / `gpio write` | replaced |
| `pistar-modemupgrade:497-510` | `/usr/local/bin/firmware/utils/stm32flash*` (armhf) on `/dev/ttyAMA0` | replaced: Ubuntu's `stm32flash` through `flash-mmdvm-hs` |
| `pistar-mmdvmhshatreset:19,48` | `platformDetect.sh` "Pi 4 Model", requires `/dev/ttyAMA0` | replaced |
| `pistar-findmodem:141,250-260` | `/dev/ttyAMA*`, Odroid / sun8i special cases | replaced |
| `pistar-nextiontext.py:34` | writes Nextion commands to `/dev/ttyAMA0` | not installed (that is the modem here) |
| `pistar-oledtext.py` | I2C OLED through `luma.oled` | not installed |
| `pistar-ap.service:14-163` | hostapd on `wlan0` / `wlan0_ap`, `ifup`, `ifconfig`, `iw ... interface add` | not installed |
| `pistar-firewall:143-148` | `wlan0_ap` rules when hostapd is configured | inactive |
| `pistar-remote:337-348,500-511` | `/sbin/iwconfig wlan0` | not installed (Python 2) |
| `pistar-bootconfig.sh:20-69` | `/boot/Pi-Star_Config_*.zip`, `/boot/firmware/...`, `wpa_supplicant.conf` from the boot partition | not installed |
| `pistar-expand`, `pistar-clone` | SD-card resize / clone, `/boot/.expanded`, `armbianEnv.txt` | not installed |
| `pistar-motdgen:46,79` | MOTD text about `rpi-rw` | not installed |
| `pistar-watchdog`, `pistar-remote`, `pistar-keeper` | `#!/usr/bin/python` (Python 2) | watchdog replaced, others not installed |

`rpi-rw` / `rpi-ro` are not defined in any of the three repositories
(**image-only**; shell aliases according to the MOTD text). bin's
`platformDetect.sh` reads `/proc/cpuinfo` `Revision` / `Hardware` and
`/proc/device-tree/model` and prints a Raspberry Pi model name, "sun8i based
Pi Clone", "Odroid XU3/XU4 System", or `Generic <uname -p> class computer`.

## 10. Things that could not be determined

- The contents of the image-only files: nginx site and `php.conf`, the
  systemd units and timers (exact dependencies, `OnStartupSec` values),
  `/etc/rc.local`, `/etc/crontab`, `/etc/fstab` (tmpfs for `/var/log`,
  `/tmp`), `/etc/passwd` / `group` entries of `mmdvm` and `pi-star`, udev
  rules, the firewall hook.
- Pi-Star's build recipe for the binaries (flags, patches beyond the version
  string, and for ircDDBGateway the compiled-in directories).
- Exact source commits of MMDVMCal, the MMDVM_CM programs, NextionDriver and
  ircDDBGateway.
- Whether `www.pistar.uk` serves the host files to a client that is not a
  Pi-Star image (the request looks the same: plain `curl` with the
  `Pi-Star_4.3.10` user agent).
