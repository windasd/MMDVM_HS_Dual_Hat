# Pi-Star functions on the Bubblegum-96: status

**Nothing in this table has been tried.** No Bubblegum-96 with the board and
no Ubuntu arm64 machine was available; the statuses are what follows from
reading the upstream code (RESEARCH.md) and from how `install-pistar.sh`
sets the system up. Read "expected" as "no reason found why not", not as
"seen working".

Status words:

- **unchanged** - upstream code runs as it is; expected to work.
- **edited** - upstream code with an edit the installer makes (named).
- **replaced** - a file from `board/` or a different mechanism does the job.
- **not available** - cannot work on this board; what the user sees instead.
- **unknown** - depends on something that could not be judged from the code.

## Dashboard (public part, `/`)

| Function | Status | Notes |
|---|---|---|
| Live view: modes, TX/RX state, frequencies, modem firmware, TCXO (`mmdvmhost/repeaterinfo.php`) | unchanged | Parses `/var/log/pi-star/MMDVM-<UTC date>.log`. Needs `FileLevel` 1 or 2 as in Pi-Star's default file |
| Gateway activity / last heard (`mmdvmhost/lh.php`), local RF activity (`localtx.php`) | unchanged | Same log; names from `/usr/local/etc/DMRIds.dat` (needs one successful host-file update) |
| Service indicators (green / red) on the left | unchanged | `pgrep` / `ps` on the program names built here |
| BrandMeister connections panel (`bm_links.php`) | unchanged | Queries the BM API over HTTPS for your DMR ID |
| D-Star panels (`dstarrepeater/*.php`: links, last heard, CCS, StarNet) | unknown | Only with `--with-dstar`; see D-Star below |
| POCSAG / DAPNET messages (`mmdvmhost/pages.php`) | unchanged | Reads the DAPNETGateway log |
| Hardware info line: host name, kernel, platform, CPU load, CPU temperature | edited | Platform: `board/platformDetect.sh` (device-tree model). Temperature: `board/pistar-b96-temp`; **shows the TMP102 outlet-air temperature, labelled "CPU Temp"**, unless the kernel provides `thermal_zone0`; shows 0 if neither exists |
| Auto-refresh (jQuery timers) | unchanged | |
| JSON / API: `/api/last_heard.php`, `/api/index.php` | unchanged | Not behind the admin login, as upstream |
| Language packs (`lang/*.php`, 24 languages incl. `chinese_tw`) | unchanged | Chosen on the configuration page; stored in `config/language.php` |
| CSS / colours (`css/pistar-css.php`, `/etc/pistar-css.ini`) | unchanged | |

## Admin page (`/admin/`)

| Function | Status | Notes |
|---|---|---|
| Login (HTTP basic auth, user `pi-star`) | replaced | nginx site written by the installer; same realm file `/var/www/.htpasswd` |
| Default-password banner and forced change (`change_password_required.php`) | unchanged | Changes the web password (`htpasswd`) and the Linux password of user `pi-star` (`chpasswd`); that user has no login shell here |
| Service status row (MMDVMHost, DMRGateway, ..., PiStar-Watchdog, PiStar-Remote, PiStar-Keeper) | unchanged | Watchdog shows running when `board/pistar-watchdog` runs. PiStar-Remote and PiStar-Keeper always red (not available) |
| BrandMeister manager (`bm_manager.php`: static TG add / drop, drop dynamic) | unchanged | Needs your BM API key in `/etc/bmapi.key` (Expert > API Keys) |
| TGIF manager, TGIF static talk groups | unchanged | Needs a TGIF key |
| YSF / P25 / NXDN / M17 link managers | unchanged | Use `sudo /usr/local/bin/RemoteCommand` (built here); the configuration page adds `[Remote Commands] Enable=1` to the gateway files when it saves (`admin/configure.php:3087-3156`) |
| D-Star link manager | unknown | `--with-dstar` only; uses `remotecontrold` |
| System info (`sysinfo.php`): memory, disks, program versions | unchanged | Version strings are upstream's (`20250828`), not Pi-Star's `..._PS4`; programs that are not built show empty |
| Live modem log (`live_modem_log.php`), download log | unchanged | |
| Power: reboot, shutdown (`power.php`) | edited | `remount,ro` removed; `sudo reboot` / `sudo shutdown -h now` as upstream. Shutdown ends at the PMIC / STM6601 behaviour of the board (study 16.10) |
| Update (`update.php` -> `pistar-update`) | replaced | `board/pistar-update`: refreshes host / ID files only and prints the installed pins. No `git pull`, no `apt` |
| Upgrade (`expert/upgrade.php` -> `pistar-upgrade`) | not available | `board/pistar-upgrade` writes "Upgrade is not available on this board" into the log the page shows. Version stays 4.3.10 |
| Backup (`config_backup.php`, download zip) | unchanged | Wi-Fi file and API keys are included; `/etc/dhcpcd.conf` does not exist and is skipped by the page |
| Restore (upload zip) | edited | `patches/dashboard/0001-...`: after installing the files, the board's modem port, UART speed and `[Nextion] Port=modem` are written back. A backup from your Raspberry Pi can be restored; its **host name** and `/etc/hosts` are restored too (upstream behaviour). A static IP from a Pi backup (`dhcpcd.conf`) is installed as a file but has no effect |
| Factory reset (button on the configuration page) | replaced | `board/pistar-factory-reset`: default configuration from `config_clean.zip` + board presets. Does not reset the dashboard / scripts (they are pinned) nor the admin password |
| Calibration (`calibration.php`, MMDVMCal over a local UDP console) | unknown | MMDVMCal is built (pin inferred). `pistar-calibration-start` chains `nc -ulp ... -s ...` and `script`; Ubuntu's `netcat-openbsd` may not accept that option form |

## Configuration page (`/admin/configure.php`)

| Section | Status | Notes |
|---|---|---|
| Control Software: MMDVMHost / DStarRepeater, Simplex / Duplex | unchanged | Choose MMDVMHost + Duplex Repeater. DStarRepeater: not available (program not built; it is for non-MMDVM modems) |
| MMDVMHost Configuration: mode switches DMR / D-Star / YSF / P25 / NXDN / M17 / POCSAG, cross modes, hang times | unchanged | Cross-mode programs YSF2DMR, YSF2NXDN, YSF2P25, DMR2YSF, DMR2NXDN are built (pin inferred). NXDN2DMR is built too, but there is no `/etc/nxdn2dmr` (none in `config_clean.zip`), so the page does not offer it |
| MMDVM Display Type / Port / Nextion Layout | unchanged | Pre-set by the installer: `Nextion`, port `modem`, layout `ON7LDS L3` (= `ScreenLayout=3`). OLED / HD44780 / TFT Serial / LCDproc: not available (no such hardware; MMDVMHost is built without them) |
| General: callsign, CCS7/DMR ID, frequencies, location, URL | unchanged | |
| Radio/Modem Type | unchanged | Use **"MMDVM_HS_Duplex_Hat (DB9MAT, DF2ET & DO7EN) for Pi (GPIO)"** (`mmdvmhsdualhatgpio`). The page writes `/dev/ttyAMA0`; that name is a udev alias of `/dev/ttyOWL2` here. Other types are selectable but describe hardware that is not on the board |
| Node type (public / private), APRS host, time zone, dashboard language | unchanged | Time zone: `timedatectl set-timezone` |
| Host name field | unchanged | sed on `/etc/hostname` and `/etc/hosts`, effective after reboot. On images using cloud-init the name may be reset at boot (`preserve_hostname`) |
| DMR: master, BM Hotspot Security, ESSID, colour code, EmbeddedLCOnly, DumpTAData | unchanged | See `configure-brandmeister.md` |
| DMR via DMRGateway (BM + DMR+ + XLX + TGIF) | unchanged | DMRGateway is built at the commit of Pi-Star's binary |
| D-Star (reflector, RPT1/2, ircDDB, time announcements) | unknown | Not built by default. `--with-dstar` builds g4klx/ircDDBGateway (pin and directories inferred) against wxWidgets 3.2 instead of Pi-Star's 3.0; never compiled |
| YSF (startup host, UPPERCASE hosts, WiresX passthrough, YSF2DMR ...) | unchanged | |
| P25, NXDN, M17 | unchanged | M17Gateway's config file is the upstream sample, not Pi-Star's file: **unknown** whether the page's M17 fields match it |
| POCSAG / DAPNET | unknown | `/etc/dapnetgateway` is the upstream sample, not Pi-Star's file |
| APRSGateway | unknown | `/etc/aprsgateway` is the upstream sample |
| Mobile GPS (MobileGPS daemon on a serial port) | not available | Section is hidden (no `/etc/mobilegps`). The GPS belongs to gpsd on `/dev/ttySC1`. **Replaced by** gpsd: the gateways are built with `USE_GPSD` and get a `[GPSD]` section with `Enable=0`; set `Enable=1` in Expert > DMR GW / YSF GW / NXDN GW if you want your position sent to the networks |
| Wireless Configuration (scan, add networks, country) | edited / unknown | Same file as on the Pi (`/etc/wpa_supplicant/wpa_supplicant.conf`), used by `wpa_supplicant@wlan0`; a path unit reloads it after saving; DHCP by netplan / networkd; country list generated. Needs the Wi-Fi interface to be called `wlan0` (a `.link` file renames a single Wi-Fi interface) and a working Wi-Fi driver in your kernel. Skipped entirely if NetworkManager or a netplan `wifis:` section already runs Wi-Fi |
| "Reset WiFi Adapter" | edited | `ifdown` / `ifup` -> `ip link set wlan0 down` / `up` |
| Auto AP (hostapd access point when no known network is found), Auto AP SSID / PSK | not available | Built on ifupdown, `wlan0_ap` and Pi-Star's captive portal. hostapd is not installed, so the fields are hidden |
| Firewall section: dashboard / ircDDB remote / SSH "Public" or "Private", uPnP | unchanged | These settings only control **uPnP port mappings on your router**. uPnP is off after installation (commented line in `/etc/crontab`); switching it on in the page runs `upnpc` every 5 minutes |
| Pi-Star firewall (`pistar-firewall`, iptables) | unchanged, optional | Not active unless installed with `--with-firewall`. It flushes all rules and sets INPUT and OUTPUT to DROP with Pi-Star's allow list; not judged against Meshtastic, gpsd / chrony or other services of this board |
| Remote access password / "pi-star" password | unchanged | See Admin page |

## Expert pages (`/admin/expert/`)

| Function | Status | Notes |
|---|---|---|
| Quick editors: MMDVMHost, DMR GW, YSF GW, P25 GW, NXDN GW, DAPNET GW | unchanged | Files staged in `/tmp`, installed with `sudo install`, service restarted |
| Quick editors: DStarRepeater, ircDDBGateway, TimeServer, StarNetServer | unknown | Files exist (defaults); the programs only with `--with-dstar` (no DStarRepeater at all) |
| Full edit: DMR GW, RSSI Dat | unchanged | |
| Full edit: PiStar-Remote | not available | The file can be edited; the program (Python 2) is not installed |
| Full edit: WiFi (`wpa_supplicant.conf`) | unchanged | See Wireless Configuration |
| Full edit: API keys (BM, DAPNET, TGIF) | unchanged | |
| Full edit: System Cron | unchanged | Edits **Ubuntu's `/etc/crontab`**; the Pi-Star jobs of this port are in `/etc/cron.d/pistar-b96`, not there |
| CSS Tool (`edit_dashboard.php`) | unchanged | |
| Modem firmware upgrade (`modem_fw_upgrade.php` -> `pistar-modemupgrade`) | replaced | `board/pistar-modemupgrade` offers one entry, `hs_dual_hat`, and flashes Pi-Star's `hs_dual_hat.bin` (MD5-checked) through `/usr/local/sbin/flash-mmdvm-hs`. All other modem ids: "not available on this board". Whether that firmware build fits the board: **unknown** |
| `pistar-mmdvmhshatflash`, `pistar-zumspotflash`, ... (old per-board flash commands) | not available | They no longer exist upstream; `pistar-modemupgrade` replaced them |
| SSH Access (shellinabox in a frame) | not available | shellinabox is not installed; the page says "SSH Feature not yet installed". Use a normal SSH client |
| Jitter test (`jitter_test.php` -> `pistar-jittertest`) | unchanged | |
| Upgrade | not available | See Admin page |

## Command line and background

| Function | Status | Notes |
|---|---|---|
| `rpi-rw`, `rpi-ro` | replaced | No-ops that say so; the root file system is always read-write |
| Read-only root file system | not available | Every `mount -o remount,ro` in the dashboard and the scripts is turned into `true` |
| `pistar-update`, `pistar-upgrade`, `pistar-factory-reset` | replaced / not available | As above |
| `pistar-firewall`, `HostFilesUpdate.sh`, `pistar-bmapi`, `pistar-tgifapi`, `pistar-dapnetapi`, `pistar-link`, `pistar-ysflink`, `pistar-p25link`, `pistar-nxdnlink`, `pistar-mmdvmremote`, `pistar-jittertest`, `pistar-mmdvmhost-module` | unchanged | |
| `pistar-mmdvmcal`, `pistar-calibration-start` | edited | `remount,ro` removed. Reads `UARTPort` / `UARTSpeed` from `/etc/mmdvmhost` |
| `pistar-findmodem`, `pistar-mmdvmhshatreset`, `pistar-modemupgrade` | replaced | Upstream versions would drive GPIO 20 / 21, which are other pins on the S900 |
| `pistar-watchdog` | replaced | bash instead of Python 2; restarts stopped daemons with back-off; does not delete system logs |
| `pistar-remote` (RF remote control), `pistar-keeper` | not available | Python 2 programs; Ubuntu 24.04 has no Python 2 |
| `pistar-nextiontext.py`, `pistar-oledtext.py` | not available | The first writes to `/dev/ttyAMA0` as if a display were there (here: the modem); no OLED |
| `pistar-expand`, `pistar-clone`, `pistar-bootconfig.sh` (config zip / `wpa_supplicant.conf` on the boot partition), `pistar-motdgen`, `pistar-sslgenerate`, `pistar-sendcw` | not available | Raspberry Pi image management, or not looked at closely enough to install |
| Daily job (host files, log clean-up) | replaced | `/etc/cron.d/pistar-b96` -> `board/pistar-b96-daily`; no git pull, no WiringPi download; logs kept 2 days |
| Hourly job (journal vacuum, nginx log trim) | not available | Not reproduced; Ubuntu's journald and logrotate settings apply |
| Logs on tmpfs | not available | `/var/log/pi-star` is on the root file system |
| Host files from www.pistar.uk | unknown | Upstream script, unchanged; whether the server serves them to this system is not known |
| NextionDriver | unchanged | Built (pin inferred), unit installed; runs only if the display port is set to `/dev/ttyNextionDriver`, which is not the set-up of this board |
| TJC display on the modem port | unknown | `Port=modem`, `ScreenLayout=3`. The screen file of `display/tjc8048x550` was drawn for MMDVM-Display's layout 3; that the old built-in driver of MMDVMHost sends the same fields has not been compared line by line |
| GPS position / time | replaced | gpsd and chrony from the board package, unchanged by this installer |
| Fan, battery shutdown, Meshtastic, Ethernet naming | replaced | Board package (`../install.sh`), independent of Pi-Star; no dashboard page |
