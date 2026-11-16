# What the MMDVM Nextion driver sends to the screen

This is the contract the screen file in this directory is built against. It was
read from source, not from a running system. Everything below is from the files
and commits named here; where the source leaves a question open it is listed in
[section 9](#9-open-points-and-oddities-in-the-source) instead of being guessed.

| Source | Commit read | Used for |
|---|---|---|
| `g4klx/MMDVM-Display` `Nextion.cpp`, `Nextion.h`, `Display.cpp`, `MMDVM-Display.cpp`, `Conf.cpp`, `ModemSerialPort.cpp`, `NextionUpdater.cpp`, `MMDVM-Display.ini` | `76cd3c3` (2026-11-05) | the driver this design targets |
| `g4klx/MMDVM-Display` `Nextion_ON7LDS/README.md`, `README-L2`, `README-L3` | same | ON7LDS field and status-code documentation |
| `g4klx/MMDVMHost` `Nextion.cpp` | `d709c2b` (2023-06-06), the last version before the display code was removed in `f12604b` (2023-06-16) | the pre-split driver, for the differences in section 8 |
| `g4klx/MMDVMHost` `DMRSlot.cpp`, `MMDVM-Host.cpp`, `Modem.cpp` | `6c849ab` (2026-11-15) | what is in the JSON the display program receives; the modem pass-through |
| `on7lds/NextionDriver` `Nextion/README-extra-fields-and-status-codes` | `03b9042` (2025-10-01) | the extra fields `t20`-`t32`, `cpuload` |

## 1. Transport

- Every instruction is ASCII text followed by three `0xFF` bytes
  (`CNextion::sendCommand`). There is no other framing.
- The driver addresses everything **by name**: `page <pagename>`,
  `<objname>.txt="..."`, `<objname>.val=N`, `MMDVM.status.val=N`,
  `click S0,1`. It never uses a page id or a component id. A name that does not
  exist on the page being shown makes the screen answer `0x1A` (or `0x03` for a
  page, `0x02` for `click`), and nothing is drawn.
- Unqualified names (`t0.txt=`) go to **whatever page the screen is showing**.
  Every page therefore needs its own `t0`, `t1`, ... with the meanings below.
- `CNextion::open` sends `bkcmd=3`, so the screen answers every instruction
  (`0x01` = done). `CNextion::clockInt` sends instructions in batches of at most
  120 bytes (`MAX_BATCH_LENGTH`) and waits for one answer per instruction before
  sending the next batch, giving up after 500 ms (`m_waitingTimer`). So the
  return line (screen TX to the modem) is needed for full speed: without it the
  screen still works, but every batch costs 500 ms.
- With `Port=modem` the bytes travel `MMDVM-Display` -> MQTT topic
  `<host>/display-in` -> `MMDVM-Host` (`CMMDVMHost::writeSerial`, pieces of at
  most 252 bytes) -> modem `MMDVM_SERIAL_DATA` (0x80) -> the modem's UART, and
  back by `<host>/display-out` (`CModemSerialPort`, `MMDVM-Host.cpp`). The baud
  rate is the modem firmware's (`SERIAL_REPEATER_BAUD`, 9600 as shipped);
  `[Nextion] Speed=` is used only for a screen on its own serial port.
- A message from the screen that starts with `0x2A` is published on
  `<name>/nextion-out`; nothing in MMDVM-Display acts on it
  (`CNextion::processReply`). Touch events and other messages are ignored.
  Anything published on `<name>/nextion-in` is sent to the screen as one
  instruction (`CNextion::writeCommandInt`).

## 2. ScreenLayout values

`CNextion::CNextion` accepts only 0, 2 and 3 (`assert`, and
`CMMDVMDisplay::createDisplay` refuses anything else with "Unknown").

| ScreenLayout | Name | Feature bits (`feature_set[]`) | What changes on the wire |
|---|---|---|---|
| 0 | G4KLX | none | Basic fields only. No talker alias, no temperature, no `t4`/`t5`. |
| 2 | ON7LDS | `TA_ENABLE`, `TA_COLOUR`, `TA_FONTSIZE` | Talker alias in `t8`/`t9`. The driver also sends **`t0.pco=0`, `t2.pco=0`** (black text), **`t0.font=4`, `t2.font=4`**, `t8.pco=1024`, `t9.pco=1024` (dark green) and `t8.font=3/2/1`, `t9.font=3/2/1` by alias length. |
| 3 | ON7LDS DIY | `TA_ENABLE`, `DIY` | Talker alias in `t8`/`t9` with **no colour or font instructions**. Adds `t4`, `t5` and the temperature `t20` on the idle page. After each item it sends `MMDVM.status.val=<code>` then `click S0,1` (`CNextion::sendCommandAction`). |
| 1, 4 | (old MMDVMHost only) | - | Not accepted by MMDVM-Display. In the old MMDVMHost 4 was "3 at 115200 baud" - a speed setting, not a higher resolution. |

### Chosen: ScreenLayout=3

- **Layout 2 forces colours and font ids.** It sends `pco=0` (black) for the DMR
  source lines and `pco=1024` (dark green) for the alias - unreadable on a dark
  theme - and font ids 1 to 4 chosen for 320 x 240 screens. Layout 3 sends no
  colour and no font instruction at all, so the screen file owns its looks.
- **Layout 3 sends more:** callsign and id separately (`t4`, `t5`) and the CPU
  temperature (`t20`). Layout 0 and 2 send neither.
- **The status codes let the screen cover a hole in the driver:** in an error
  state the current driver sends no text at all (section 9, point 1); only
  layout 3 tells the screen, by status 13, that it happened.
- **Cost:** each item costs two more instructions (about 36 bytes). At 9600 baud
  a DMR call start is about 0.3 s of serial time. The price of layout 3 is that
  the screen **must** have a global variable `status` on page `MMDVM` and an
  object `S0` on every page.

"High resolution" is not a driver setting: there is none. The driver sends the
same text whatever the panel; resolution is entirely the screen file's business.

## 3. Page names

Sent by `page <name>`; names are case-sensitive.

| Page name | Sent by | When |
|---|---|---|
| `MMDVM` | `setIdleInt`, `setErrorInt`, `setLockoutInt`, (`setQuitInt`) | idle, error, lockout. Sent again every time the idle page is redrawn. |
| `DStar` | `writeDStarInt` | first D-Star header after another mode |
| `DMR` | `writeDMRInt` | first DMR start after another mode |
| `YSF` | `writeFusionInt` | first YSF start |
| `P25` | `writeP25Int` | first P25 start |
| `NXDN` | `writeNXDNInt` | first NXDN start |
| `POCSAG` | `writePOCSAGInt` | first POCSAG message |
| `FM` | `writeFMInt` | first FM state other than "listening" |

There is no M17 page in MMDVM-Display (the old MMDVMHost had `page M17`). The
stock G4KLX and ON7LDS `.HMI` files in the repository contain pages MMDVM, DStar,
DMR, YSF, P25, NXDN, POCSAG and M17 - **no `FM` page** - so with them an FM
state writes into whatever page is showing. This design has an `FM` page.

## 4. Sent on every page

| Instruction | Function | When |
|---|---|---|
| `bkcmd=3` | `open` | once at start |
| `dim=<Brightness>` | every `write...Int`, `setErrorInt`, `setLockoutInt` | at each call start / header, only if `Brightness` > 0 |
| `dim=<IdleBrightness>` | `setIdleInt` | on going idle, only if `Brightness` > 0 |
| `MMDVM.status.val=<n>` + `click S0,1` | `sendCommandAction` | layout 3 only, after each item; codes in section 7. The first is `status 0` straight after `bkcmd=3`, on whatever page the screen is showing at power-on. |

`click S0,1` runs the **Touch Press** event of `S0`.

## 5. Page `MMDVM`

| Object | Type needed | Text written | Function | When |
|---|---|---|---|---|
| `t0` | Text | `"<callsign>/<id>"`, or `"<callsign>"` if the id is 0 | `setIdleInt` | each idle redraw |
| `t0` | Text | `"LOCKOUT"` | `setLockoutInt` | host mode "lockout" |
| `t0` | Text | `"MMDVM STOPPED"` | `setQuitInt` | never, in MMDVM-Display: nothing calls `CDisplay::setQuit` (section 9, point 14). The old MMDVMHost sent it on exit. |
| `t1` | Text | `"MMDVM IDLE"` | `setIdleInt`, `clearCWInt` | idle |
| `t1` | Text | `"Sending CW Ident"` | `writeCWInt` | host mode "CW" |
| `t2` | Text | `strftime("%x %X")` - date and time in the **locale of the MMDVM-Display process**, local time or UTC (`UTC=`) | `sendClock` | with each idle redraw and then every 400 ms (`m_clockDisplayTimer`) while idle or CW; only if `DisplayClock=1` |
| `t3` | Text | IPv4 address, else IPv6 address, else `"(ip unknown)"` | `setIdleInt` | each idle redraw |
| `t4` | Text | `"<callsign>"` | `setIdleInt` | layout 3 only |
| `t5` | Text | `"<id>"`, or `""` if the id is 0 | `setIdleInt` | layout 3 only |
| `t20` | Text | `"?"` | `setIdleInt` | layouts 0 and 2 only (!) |
| `t20` | Text | `"%2.1f \xB0C"` e.g. `45.2 °C`, or `°F` with `[General] TemperatureInF=1`. The degree sign is the **single byte 176 (0xB0)**. | `sendCPU` | layout 3 only, and only once a temperature is known |
| `t21` | Text | `"%0.0f MHz"` (CPU clock / 1000), or `"?"` | `sendCPU` | each idle redraw; in layout 3 also on every CPU report while idle (`writeCPUInt`) |
| `t22` | Text | `"%0.2f"` (system load), or `"?"` | `sendCPU` | same |
| `cpuload` | anything with `.val` | `cpuload.val=<load x 100>`, or `0` | `sendCPU` | same |
| `t30` | Text | `"%.4f MHz"` RX frequency, or `"?"` | `setIdleInt` | each idle redraw |
| `t32` | Text | `"%.4f MHz"` TX frequency, or `"?"` | `setIdleInt` | each idle redraw |
| `t31` | Text | location - always `"?"` (section 9, point 4) | `setIdleInt` | each idle redraw |
| `status` | Variable, **global** | `MMDVM.status.val=<n>` | `sendCommandAction` | layout 3 |
| `S0` | any object with a Touch Press event | `click S0,1` | `sendCommandAction` | layout 3 |

Where the values come from (`MMDVM-Display.cpp`): callsign, id and frequencies
from the host's configuration, asked for over MQTT (`parseHostConfig`); the IP
address from the first interface MMDVM-Info reports (`parseAddresses`);
temperature, CPU clock and load from MMDVM-Info's periodic CPU message
(`parseCPU`). Without MMDVM-Info running, `t3` is `(ip unknown)`, `t21` and `t22`
are `?`, and `t20` is never written.

The idle page is redrawn in full (`page MMDVM` and every field again) whenever
the host goes idle and whenever the callsign, id, frequencies or address change
while idle (`redrawIdle`).

## 6. Mode pages

`<R/N>` is `R` for RF and `N` for network.

### `DStar`

| Object | Text written | Function | When |
|---|---|---|---|
| `t0` | `"<R/N> <my1, max 8>/<my2, 4>"` | `writeDStarInt` | header (start or late entry) |
| `t1` | `"<your, max 8>"` | `writeDStarInt` | header |
| `t2` | `"via <reflector, max 8>"` | `writeDStarInt` | header, unless the reflector is eight spaces |
| `t3` | `"<n>dBm"` | `writeDStarRSSIInt` | each RSSI report |
| `t4` | `"<n.n>%"` | `writeDStarBERInt` | each BER report |
| `t5` | slow-data text message, 20 characters | `writeDStarTextInt` | when decoded |
| `t0` | `"Listening"`; `t1`...`t5` set to `""` | `clearDStarInt` | end of transmission |

### `DMR`

| Object | Slot | Text written | Function | When |
|---|---|---|---|---|
| `t0` | 1 | `"1 <R/N> <src_info>"` | `writeDMRInt` | start or late entry |
| `t1` | 1 | `"TG<dst>"` (group) or `"<dst>"` (private) | `writeDMRInt` | start |
| `t4` | 1 | `"<n>dBm"` | `writeDMRRSSIInt` | each RSSI report |
| `t6` | 1 | `"<n.n>%"` | `writeDMRBERInt` | each BER report |
| `t8` | 1 | talker alias so far | `writeDMRTAInt` | layouts 2 and 3, each time more of it is decoded |
| `t0` | 1 | `"1 Listening"`; `t1`, `t4`, `t6`, `t8` set to `""` | `clearDMRInt` | end of the slot 1 call |
| `t2` | 2 | `"2 <R/N> <src_info>"` | `writeDMRInt` | start or late entry |
| `t3` | 2 | `"TG<dst>"` or `"<dst>"` | `writeDMRInt` | start |
| `t5` | 2 | `"<n>dBm"` | `writeDMRRSSIInt` | |
| `t7` | 2 | `"<n.n>%"` | `writeDMRBERInt` | |
| `t9` | 2 | talker alias | `writeDMRTAInt` | layouts 2 and 3 |
| `t2` | 2 | `"2 Listening"`; `t3`, `t5`, `t7`, `t9` set to `""` | `clearDMRInt` | end of the slot 2 call |

When the page is first shown, `writeDMRInt` writes `"<n> Listening"` into the
**other** slot's source line, then the call into its own. `src_info` is the
callsign from the DMR id table, or the id as digits if it is not in the table
(`CDMRLookup::find`).

### `YSF`

| Object | Text written | Function | When |
|---|---|---|---|
| `t0` | `"<R/N> <source, max 10>"` | `writeFusionInt` | start or late entry |
| `t1` | `"DG-ID <n>"` | `writeFusionInt` | start |
| `t2` | `"at <reflector, max 10>"` | `writeFusionInt` | start, unless the reflector is ten spaces |
| `t3` | `"<n>dBm"` | `writeFusionRSSIInt` | each RSSI report |
| `t4` | `"<n.n>%"` | `writeFusionBERInt` | each BER report |
| `t0` | `"Listening"`; `t1`...`t4` set to `""` | `clearFusionInt` | end |

### `P25` and `NXDN` (identical)

| Object | Text written | Function | When |
|---|---|---|---|
| `t0` | `"<R/N> <source, max 10>"` | `writeP25Int` / `writeNXDNInt` | start or late entry |
| `t1` | `"TG<dst>"` or `"<dst>"` | same | start |
| `t2` | `"<n>dBm"` | `writeP25RSSIInt` / `writeNXDNRSSIInt` | each RSSI report |
| `t3` | `"<n.n>%"` | `writeP25BERInt` / `writeNXDNBERInt` | each BER report |
| `t0` | `"Listening"`; `t1`...`t3` set to `""` | `clearP25Int` / `clearNXDNInt` | end |

### `POCSAG`

| Object | Text written | Function | When |
|---|---|---|---|
| `t0` | `"RIC: <n>"` | `writePOCSAGInt` | each message |
| `t1` | the message text (the buffer holds about 190 characters) | `writePOCSAGInt` | each message |
| `t0` | `"Waiting"`; `t1` set to `""` | `clearPOCSAGInt` | end |

### `FM`

| Object | Text written | Function | When |
|---|---|---|---|
| `t0` | `"R: Kerchunk"`, `"R: Relaying"`, `"R: Wait"`, `"R: Timeout"`, `"N: Kerchunk"`, `"N: Relaying"`, `"N: Wait"`, `"N: Timeout"`, or the raw state name for any state not in that list | `writeFMInt` (texts chosen in `CMMDVMDisplay::parseFM`) | each FM state change |
| `t2` | `"<n>dBm"` | `writeFMRSSIInt` | each RSSI report |
| `t0` | `"Listening"`; `t2` set to `""` | `clearFMInt` | state "listening" |

There is no `t1` on the FM page.

## 7. Status codes (layout 3)

Sent as `MMDVM.status.val=<n>` followed by `click S0,1`, **after** the field
they describe. Codes in MMDVM-Display's `Nextion.cpp`, with the ON7LDS
meaning (`README-L3`):

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| 0 | start-up (`open`) | 61 / 69 | DMR slot 1 / 2 listening |
| 1 | page MMDVM | 62 / 70 | DMR source (`t0` / `t2`) |
| 2 | page DStar | 63 / 71 | DMR talker alias (`t8` / `t9`) |
| 3 | page DMR | 65 / 73 | DMR destination (`t1` / `t3`) |
| 4 | page YSF | 66 / 74 | DMR RSSI (`t4` / `t5`) |
| 5 | page P25 | 67 / 75 | DMR BER (`t6` / `t7`) |
| 6 | page NXDN | 81 | YSF listening |
| 7 | page POCSAG | 82, 83, 84, 86 | YSF source, DG-ID, reflector, BER |
| 9 | page FM | 101 | P25 listening |
| 11 | idle (`t1`) | 102, 103, 104, 105 | P25 source, destination, RSSI, BER |
| 12 | CW ident (`t1`) | 121 | NXDN listening |
| 13 | error | 122, 123, 124, 125 | NXDN source, destination, RSSI, BER |
| 15 | lockout (`t0`) | 132, 133 | POCSAG RIC, message |
| 16 | IP address (`t3`) | 134 | POCSAG waiting |
| 17 | callsign / id (`t0`, `t4`, `t5`) | 147 | FM state (`t0`) |
| 19 | stopped (`t0`) - in the source, never reached (section 9, point 14) | 148 | FM RSSI (`t2`) |
| 22 | temperature (`t20`) | 149 | FM listening |
| 41 | D-Star listening | 42, 45, 46, 47, 48, 49 | D-Star source, your, reflector, RSSI, BER, text |

Documented by ON7LDS but **not** sent by MMDVM-Display: 14 (ERROR), 20, 21, 23
(RX frequency, TX frequency, location), 64 / 72 (DMR call end), 76 / 77 (GPS),
85 (YSF RSSI). The old MMDVMHost sent 14, 20, 21, 64 and 72.

## 8. Differences from the pre-2023 MMDVMHost driver

The study (section 6.3) keeps the older MMDVMHost as a fallback. The same screen
file works with it; these fields behave differently:

| Item | Old MMDVMHost (`d709c2b`) | MMDVM-Display (`76cd3c3`) |
|---|---|---|
| ScreenLayout | 0-4; 4 = layout 3 at 115200 | 0, 2, 3 |
| Talker alias | replaces the source line: `t0` / `t2` = `"<n> <R/N> <alias>"` | separate fields `t8` / `t9` |
| RSSI | `"-<n>dBm"`, averaged | `"<n>dBm"` (signed) |
| `t30`, `t32` | `"%3.6f"`, no unit, layout 3 only | `"%.4f MHz"`, all layouts |
| `t21`, `t22`, `cpuload`, `t31` | not sent (they were NextionDriver fields) | sent |
| D-Star text `t5`, FM page | no | yes |
| Error | `t0` = error text, `t1` = `"ERROR"`, status 13 then 14 | status 13 only (section 9) |
| FM | `page MMDVM`, `t0` = `"FM"`, status 18 | `page FM` |
| `bkcmd` | 0 (no answers) | 3 |
| Idle redraw | on going idle | also on every configuration / address change |

In the ON7LDS documentation `t8`-`t13` on the DMR page are GPS fields written by
NextionDriver. MMDVM-Display reuses `t8` and `t9` for the talker alias.

## 9. Open points and oddities in the source

1. **Error state sends no text.** `setErrorInt` builds `t0.txt="ERROR"` with
   `sprintf` but never passes it to `sendCommand`; only `page MMDVM`, `dim`, and
   (layout 3) status 13 go out. With layouts 0 and 2 an error is invisible. This
   design's `S0` script writes `ERROR` itself on status 13. Looks like a bug, not
   intent; it may be fixed upstream later, which would not break anything here.
2. **Clock format is the host's locale** (`setlocale(LC_TIME, "")`, `%x %X`).
   With `LC_TIME=C` it is `11/16/26 14:30:00`. With a Chinese locale it would be
   multi-byte text that this screen file's fonts cannot show. BUILD.md sets
   `LC_TIME=C` for the service. What the user's system has now is not known.
3. **`t20` is `"?"` only in layouts 0 and 2**, and written as a temperature only
   in layout 3. In layout 3 with no temperature report the field is never
   written, so it keeps the screen file's initial text (empty here).
4. **Location is always `"?"`.** The code that reads it in `parseHostConfig` is
   commented out. `t31` is kept on the page, hidden.
5. **`cpuload` is marked "TODO this is incorrect" in the source.** It is the load
   average x 100, which is not a percentage and can exceed 100. Kept as a
   Variable and not displayed.
6. **Empty reflector.** `parseDStar` and `parseYSF` pass an empty string when the
   JSON has no reflector, but the driver only suppresses the field for a string
   of 8 (or 10) spaces. So `t2` can become `"via "` or `"at "` with nothing
   after it. The `S0` scripts blank those.
7. **YSF RSSI has no status code** (`writeFusionRSSIInt` does not call
   `sendCommandAction`); the text is still written. No effect here.
8. **The type of `S0` in the ON7LDS files** could not be read: `.HMI` is a binary
   format and the editor is not installed. Only its name, its Touch Press code
   and the global Variable `status` on page `MMDVM` were confirmed from strings
   in `Nextion_ON7LDS/NX4832T035-L3.HMI`. This design uses a Hotspot; any
   component with a Touch Press event answers `click S0,1`.
9. **Text longer than `txt_maxl`.** Whether a TJC screen cuts the text or rejects
   the instruction (`0x1C`) was not verified. `txt_maxl` in `layout.json` is set
   at or above the longest text the driver's buffers can produce.
10. **RSSI and BER depend on the modem.** `CDMRSlot::writeJSONRSSI` returns early
    when the modem reports no RSSI. Whether the MMDVM_HS firmware on this board
    reports RSSI for each mode was not checked; the fields may simply stay empty.
11. **TJC against Nextion.** The instructions used (`page`, `.txt=`, `.val=`,
    `.pco=`, `dim=`, `bkcmd=`, `click`, `bauds=`, `touch_j`) are common to both
    instruction sets as documented, but nothing here has been run on a TJC X5.
12. **Talker alias encoding.** The alias is forwarded as received
    (`CDMRSlot::writeJSONText`). Anything outside ISO-8859-1 (a Chinese alias,
    for instance) will show as wrong characters.
13. **Loading a `.tft` through the modem.** `NextionUpdater` in MMDVM-Display has
    a `Port=modem` path (`uploadViaMQTT`: `whmi-wri <size>,9600,0`, 4096-byte
    blocks, 4 s per block). 4096 bytes take 4.3 s at 9600 baud, longer than its
    own timeout, and the MMDVM_HS serial repeater drops data when its 256-byte
    buffer fills. Treated as unusable for this multi-megabyte file; BUILD.md uses
    the microSD card.
14. **"MMDVM STOPPED" is never sent.** `CNextion::setQuitInt` exists (status 19),
    but nothing in MMDVM-Display calls `CDisplay::setQuit`; on exit the program
    only closes the port. The screen keeps its last picture when the software
    stops. The `S0` script still handles status 19, for the old MMDVMHost.
