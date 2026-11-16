# From a fresh install to DMR on BrandMeister, with the Pi-Star pages

**Untested.** The steps follow the code of the pinned dashboard
(`admin/configure.php`) and the Pi-Star service wrappers; they have not been
carried out on the board, and no login to a BrandMeister master was tried.
Field names are the English (UK) labels of the dashboard.

## 0. Before you start

- BrandMeister account with your DMR ID, on <https://brandmeister.network>.
- In **SelfCare** (top right, your callsign > SelfCare): switch
  **Hotspot Security** on and set a password. This is the password the
  hotspot logs in with. Do it first: the default file Pi-Star starts from
  contains a placeholder password, and if the field in step 3 is left empty
  that placeholder is what gets sent.
- The modem has firmware (see "Modem firmware" at the end) and
  `/dev/ttyOWL2` exists.
- `sudo bash install-pistar.sh` has run and the board was rebooted.

## 1. What the installer has already set

In `/etc/mmdvmhost` (Pi-Star's default file from `config_clean.zip`, then
`board/pistar-b96-presets --defaults`):

| Section | Key | Value | Why |
|---|---|---|---|
| `[Modem]` | `Port`, `UARTPort` | `/dev/ttyAMA0` | udev alias of `/dev/ttyOWL2`; the name the page writes for GPIO hats |
| `[Modem]` | `Protocol` | `uart` | |
| `[Modem]` | `UARTSpeed` | `115200` | host baud rate of the MMDVM_HS firmware |
| `[General]` | `Duplex` | `1` | two ADF7021 |
| `[General]` | `Display` | `Nextion` | TJC screen |
| `[Nextion]` | `Port` | `modem` | the screen hangs on the modem's pass-through port |
| `[Nextion]` | `ScreenLayout` | `3` | "ON7LDS L3"; `display/tjc8048x550` is drawn for 3 |

Everything else is Pi-Star's default: callsign `M1ABC`, ID `1234567`, all
modes off, 438.800 MHz. With those placeholders no radio service starts
(the wrappers refuse), and until the first "Apply" there is no
`/etc/dstar-radio.mmdvmhost`, so the dashboard shows "No Mode Defined".

Not pre-set, on purpose: callsign, DMR ID, frequencies, DMR master,
passwords, the modem type selection (step 2 writes it).

## 2. First page: Configuration

Open `http://<board address>/admin/configure.php`. Log in as `pi-star`
(password: what you typed during installation, or Pi-Star's default - see
README.md; change it at the bottom of this page: "Remote Access Password",
"Set Password").

Pi-Star shows the sections step by step; press **Apply Changes** after each
block and wait for the page to reload (it stops and restarts the services
each time).

**Control Software**

| Field | Choose |
|---|---|
| Controller Software | `MMDVMHost` |
| Controller Mode | `Duplex Repeater` |

Apply. `/etc/dstar-radio.mmdvmhost` now exists and the other sections appear.

**MMDVMHost Configuration**

| Field | Choose |
|---|---|
| DMR Mode | on |
| all other modes | off (as you had it on Pi-Star) |
| MMDVM Display Type | `Nextion`, Port `modem`, Nextion Layout `ON7LDS L3` (already selected) |

Apply. The "DMR Configuration" section appears.

**General Configuration**

| Field | Value |
|---|---|
| Node Callsign | your callsign |
| CCS7/DMR ID | your 7-digit DMR ID |
| Radio Frequency RX / TX | two frequencies (duplex), e.g. 5 MHz apart, inside your band plan; RX is what the hotspot *receives* |
| Latitude, Longitude, Town, Country, URL | as you like; they are sent to the master |
| **Radio/Modem Type** | **`MMDVM_HS_Duplex_Hat (DB9MAT, DF2ET & DO7EN) for Pi (GPIO)`** |
| Node Type | `Private` (only your DMR ID may use the hotspot) or `Public` |
| System Time Zone, Dashboard Language | as you like (`chinese_tw` exists) |

About the modem type: the board is an MMDVM_HS_Dual_Hat (STM32, two
ADF7021, 14.7456 MHz TCXO) on a serial port that is not a Raspberry Pi GPIO
UART. In Pi-Star's list, "(GPIO)" only means "the port is `/dev/ttyAMA0`".
That choice (`mmdvmhsdualhatgpio`, `admin/configure.php:2243-2251`) sets
`[Modem] Port=/dev/ttyAMA0`, `Protocol=uart`, `UARTPort` to the same,
`Duplex=1`, FM off, and nothing GPIO-related. `/dev/ttyAMA0` exists here as
an alias of `/dev/ttyOWL2`. Do **not** pick the "(USB)" variant
(`/dev/ttyACM0`), a ZUMspot / DV-Mega entry, or an entry with "12.xxxMHz".
The page does not set `UARTSpeed` for this type; the installer's `115200`
stays.

Apply.

## 3. DMR Configuration

| Field | Value |
|---|---|
| DMR Master (MMDVMHost) | a `BM_...` entry: the master you used before. BrandMeister lists no master in Taiwan (checked 2026-11-16, see `../README.md`); nearest are 4501 South Korea, 4602 China, 5021 Malaysia, 5151 Philippines |
| Hotspot Security | the SelfCare Hotspot Security password. The row appears after a `BM_` master has been selected **and applied** (`admin/configure.php:4759-4762`), so: choose the master, Apply, then enter the password, Apply again |
| ESSID (if the page shows it) | `None` for one hotspot; 01-99 if you run several under one ID |
| DMR Colour Code | `1` (must match the radio's channel) |
| DMR EmbeddedLCOnly, DMR DumpTAData | defaults |

Apply.

What this does (`admin/configure.php:1513-1540`): `[DMR Network]`
`Address` / `RemoteAddress` = the master, `Port` / `RemotePort`,
`Type=Direct`, `Password` = your Hotspot Security password. MMDVMHost logs
in to the master itself - the same as on your Raspberry Pi, and different
from the minimal package, where DMRGateway does it. DMRGateway is only
started when the master entry **`DMRGateway`** is chosen (for BrandMeister
plus DMR+ / XLX / TGIF at the same time); then the page shows "BrandMeister
Master", "BM Hotspot Security" and "BrandMeister Network ESSID" instead.

The password is stored in clear text in `/etc/mmdvmhost` (and
`/etc/dstar-radio.mmdvmhost`), mode 644, as on every Pi-Star.

The list of masters comes from `/usr/local/etc/DMR_Hosts.txt`. If the
drop-down is empty, the host files were never downloaded: run
`sudo pistar-update` (or Admin > Update) with the network up.

## 4. Check

- Dashboard (`/`): "DMR" green under Modes Enabled, "DMR Net" green, the
  master's name under "DMR Master", the modem firmware version in the
  Radio Info box.
- Admin > Live Logs: lines `DMR, Logged into the master successfully`.
  `Login to the master has failed` = wrong Hotspot Security password, or
  Hotspot Security not enabled in SelfCare.
- Radio: channel with TX = the hotspot's RX frequency, RX = the hotspot's TX
  frequency, colour code 1, time slot 2, talk group as contact. Key up on
  TG 9990 (BrandMeister parrot, private call) to hear yourself back.

## 5. Static talk groups

As before, on the BrandMeister web site: open your hotspot in SelfCare
("My hotspots"; the menu names are from memory, the site was not opened
while writing this) and add the talk groups as static for slot 2 (a duplex
hotspot also has slot 1). Changes apply on the master; nothing is stored on
the board.

Optional, to do the same from the dashboard (Admin page, BrandMeister
manager): create an API key in your BrandMeister profile and paste it in
Expert > API Keys. The manager reads `/etc/bmapi.key`
(`mmdvmhost/bm_manager.php:38`).

## 6. Coming from your Raspberry Pi

Admin > Backup/Restore on the old Pi-Star gives a zip that can be restored
here instead of steps 2-3. The restore page is patched to put the modem
port, UART speed and `[Nextion] Port=modem` back afterwards
(`patches/dashboard/0001-...`). It also restores the old **host name**, and
the Wi-Fi networks of the Pi. Check Radio/Modem Type afterwards.

## Modem firmware

Either `sudo flash-mmdvm-hs <file.bin>` (board package), or Expert > FW >
"MMDVM_HS_Dual_Hat (14.7456MHz TCXO) GPIO", which flashes the
`hs_dual_hat.bin` Pi-Star ships. That file was not examined: whether its
serial-repeater baud rate matches the TJC screen (`bauds=` in the screen
file, study section 6.3) is not known. If the display stays dark after
flashing it while DMR works, that is the first thing to look at.

## If it does not work

| Symptom | Look at |
|---|---|
| Page loads without styles / "File not found" | `/var/log/nginx/error.log`; `systemctl status php8.3-fpm` |
| "Apply" seems to do nothing, values come back unchanged | sudo: `sudo -l -U www-data`; denied commands are in `journalctl -t sudo` and in the nginx error log |
| MMDVMHost red on the dashboard | `sudo /usr/local/sbin/mmdvmhost.service start` prints why it refuses; `ls -l /dev/ttyAMA0 /dev/ttyOWL2` (alias present? group `mmdvm`?); newest `/var/log/pi-star/MMDVM-*.log` |
| Log: `Unable to read the firmware version` | modem held in reset or in the boot loader: `sudo mmdvm-gpio status`, `sudo pistar-mmdvmhshatreset`; baud rate |
| DMR Net red | master / password; outbound UDP to the master's port (62031) blocked? |
