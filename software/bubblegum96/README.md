# Host software for the r3.0-study mezzanine on a Bubblegum-96

Ubuntu 24.04 (arm64) side of the board in `hardware/r3.0-study/`: MMDVM dual
ADF7021 hotspot (STM32), Meshtastic radio (RAK4630), GPS (MAX-M10S), 1S4P
battery system, fan, LAN7500 Ethernet.

**Nothing in this directory has been run.** The board has never been built,
no Bubblegum-96 was available, the device tree was not compiled (no `dtc` on
the machine it was written on) and `install.sh` was never executed. The shell
scripts pass `bash -n`; that is the only check performed. Read
"Untested / assumptions" before relying on any file.

Design record: `docs/meshtastic-gps-study.md` (sections 2, 3, 6, 8, 10-13,
16.10). Nets and I2C addresses: `hardware/r3.0-study/gen/r30_parts.py` and
`r30_parts2.py`.

## Files

| File | Installed as | Purpose |
|---|---|---|
| `dts/mmdvm-mesh-overlay.dts` | (manual) | Device-tree overlay: `uart2` + `serial2` alias, SC16IS752, EMC2301, TMP102, INA226, MAX17048, BQ25895, `pps-gpio`, `gpio-keys` (power key), `gpio-poweroff` (disabled) |
| `dts/build-dtbo.sh` | - | Compiles the overlay; optionally merges it into the base DTB with `fdtoverlay` |
| `gpio/mmdvm-gpio.sh` | `/usr/local/sbin/mmdvm-gpio` | BOOT0 / STM32 reset / RAK4630 reset / GPS switch through sysfs GPIO |
| `gpio/mmdvm-gpio-init.service` | `/etc/systemd/system/` | Drives those lines to their idle state at boot |
| `mmdvm/MMDVM.ini` | `/etc/MMDVM-Host.ini` | MMDVM-Host configuration (upstream renamed the file and the binary to `MMDVM-Host`) |
| `mmdvm/MMDVM-Display.ini` | `/etc/MMDVM-Display.ini` | MMDVM-Display: `[Nextion] Port=modem` for the TJC screen |
| `mmdvm/build.sh` | - | Installs build dependencies, clones and builds MMDVM-Host and MMDVM-Display |
| `mmdvm/mmdvmhost.service`, `mmdvm/mmdvm-display.service` | `/etc/systemd/system/` | systemd units |
| `mmdvm/flash-mmdvm-hs.sh` | `/usr/local/sbin/flash-mmdvm-hs` | `stm32flash` wrapper using GPIO-A / GPIO-B |
| `fan/mmdvm-fan.sh`, `.service`, `.default` | `/usr/local/sbin/mmdvm-fan`, unit, `/etc/default/mmdvm-fan` | Temperature curve: TMP102 -> EMC2301 PWM, hwmon paths found by name at run time |
| `gps/gpsd.default` | `/etc/default/gpsd` | gpsd on `/dev/ttySC1`, read-only |
| `gps/chrony-gps-pps.conf` | `/etc/chrony/conf.d/mmdvm-gps-pps.conf` | chrony: NMEA via gpsd SHM + `/dev/pps0` |
| `meshtastic/README.md` | - | Host link to the RAK4630, first-boot steps, STM32 flashing notes |
| `meshtastic/provision.sh` | `/usr/local/sbin/mmdvm-mesh-provision` | Meshtastic settings of study section 10.3 |
| `network/10-mmdvm-lan7500.link` | `/etc/systemd/network/` | Names the LAN7500 (`smsc75xx`) interface `lan0` |
| `network/60-mmdvm-lan.yaml` | `/etc/netplan/` | DHCP on `lan0` |
| `network/kernel-config.fragment` | - | Kernel options everything above needs |
| `install.sh` | - | Copies the files into place |

## Host interfaces

Checked against the Bubblegum-96 hardware manual V1.1 (section 5, LS connector
table) and the `gpio-line-names` table of mainline `s900-bubblegum-96.dts`;
the two agree with each other and with study section 3.4.

| LS pin | 96Boards | S900 | Linux | Use |
|---|---|---|---|---|
| 5 / 7 | UART0 TxD / RxD | UART2, GPIOB15 / GPIOB14 | `/dev/ttyOWL2` | MMDVM modem (STM32 USART1), 115200 |
| 11 / 13 | UART1 | UART5, GPIOA27 / GPIOA25 | `/dev/ttyOWL5` | console (unchanged) |
| 15 / 17 | I2C0 SCL / SDA | I2C1, GPIOB22 / GPIOB23 | `&i2c1` | 0x48 SC16IS752, 0x2f EMC2301, 0x49 TMP102, 0x40 INA226, 0x36 MAX17048, 0x6a BQ25895 |
| 23 | GPIO-A | GPIOA0 | line 0 | out: STM32 BOOT0 |
| 24 | GPIO-B | GPIOA1 | line 1 | out: STM32 NRST (low = reset) |
| 25 | GPIO-C | GPIOA2 | line 2 | in: SC16IS752 IRQ |
| 26 | GPIO-D | GPIOA3 | line 3 | in: charger INT + gauge ALRT |
| 27 | GPIO-E | GPIOA4 | line 4 | in: power-key request (STM6601 INT) |
| 28 | GPIO-F | GPIOA5 | line 5 | out: power hold, only with JP2 2-3 |
| 29 | GPIO-G | GPIOA6 | line 6 | out: RAK4630 reset (low = reset) |
| 30 | GPIO-H | GPIOA7 | line 7 | in: GPS PPS |
| 31 | GPIO-I | GPIOA8 | line 8 | in: GPS power-switch state |
| 32 | GPIO-J | GPIOA9 | line 9 | in: EMC2301 ALERT (not used by software) |

All six I2C devices are on the 3.3 V always-on bus behind the TCA9406 (U34)
and are reachable by the host. The nRF52840 is not on that bus.

`/dev/ttySC0` = SC16IS752 channel A = Meshtastic serial API,
`/dev/ttySC1` = channel B = GPS NMEA (receive only).

## Installation order

The scripts were written on Windows and carry no executable bit in the
working tree: run them as `bash <script>` or `chmod +x` them first.

1. **Kernel.** Merge `network/kernel-config.fragment` into the kernel config
   and rebuild. Build the DTBs with symbols: `make DTC_FLAGS=-@ dtbs`.
2. **Device tree.** `KSRC=<kernel tree> dts/build-dtbo.sh <base.dtb>` and
   install the merged DTB where the boot loader loads it from (or apply the
   `.dtbo` in U-Boot, or include the file in the board `.dts`; see the
   header of the overlay). Reboot. Check: `/dev/ttyOWL2`, `/dev/ttySC0`,
   `/dev/ttySC1`, `/dev/pps0`, `sensors`, `ls /sys/class/power_supply`.
3. **Packages.**
   `sudo apt-get install -y mosquitto mosquitto-clients stm32flash gpsd gpsd-clients chrony pps-tools lm-sensors i2c-tools gpiod pipx`
4. **MMDVM build.** `mmdvm/build.sh`
5. **Files.** `sudo ./install.sh --dry-run`, then `sudo ./install.sh`
6. **GPIO defaults and fan.** `sudo systemctl enable --now mmdvm-gpio-init mmdvm-fan`
7. **STM32 firmware** (if the modem is blank):
   `sudo flash-mmdvm-hs mmdvm_hs_dual_hat_fw.bin`
8. **MMDVM.** Edit `/etc/MMDVM-Host.ini` (callsign, DMR ID, frequencies, colour
   code), then `sudo systemctl enable --now mosquitto mmdvmhost mmdvm-display`.
   Log: `mosquitto_sub -t 'host/#' -v` and `journalctl -u mmdvmhost`.
9. **GPS / time.** `sudo systemctl enable gpsd && sudo systemctl restart gpsd chrony`;
   check with `gpsmon`, `sudo ppstest /dev/pps0`, `chronyc sources`.
10. **Meshtastic.** `pipx install meshtastic`, then follow
    `meshtastic/README.md` (first provisioning over USB or BLE).
11. **Network.** `sudo netplan try`; `ip link show lan0`.

## Design decisions that differ from the study text

- **Fan controller.** The study (3.4, 4.2, 7.3, 8) names an AMC6821. The
  schematic generator and the BOM have an EMC2301 (0x2f) plus a TMP102
  (0x49). The software follows the schematic: `microchip,emc2305` driver, and
  a service instead of `fancontrol` (the driver has no `pwm1_enable`). The
  EMC2301 has no temperature input and no stand-alone curve, so unlike the
  AMC6821 described in 7.3 the fan does not regulate itself if the host hangs.
- **Program and file names.** Upstream is now `MMDVM-Host` /
  `/etc/MMDVM-Host.ini`; there is no `[Nextion]` section in the host file any
  more. The display is configured only in `MMDVM-Display.ini`.
- **`gpio-poweroff` is present but disabled**, because the board default
  (JP2 1-2) does not connect GPIO-F to anything.
- **`gpio-keys` on GPIO-E** was added so the power key causes a normal
  shutdown (section 3.4 lists the line; section 8 does not list software for it).
- **`gpio-line-names` is not in the overlay**: mainline already names the LS
  lines `GPIO-A` .. `GPIO-L`, and an overlay could only replace the whole
  146-entry table.
- **`gpio/`** is not in the study's software list. It exists because of the
  floating inputs described below.

## Untested / assumptions

Everything is untested. The items below are the ones most likely to be wrong
or that need a decision; each has a matching `TODO` or note in the file.

Device tree (`dts/mmdvm-mesh-overlay.dts`)

1. Never compiled. Syntax and `&{/aliases}` / `&{/}` handling unverified.
2. The boot chain of the user's image is unknown; overlay application
   (build-time `fdtoverlay`, U-Boot `fdt apply`, or static include) is the
   user's choice. The base DTB needs `-@` for the first two.
3. `uart2` has no pinctrl entry: `pinctrl-s900.c` only has a `uart2_dummy`
   group for the RX/TX pads. Assumed to mean the pads need no mux setting.
4. `owl-uart` needs the `serial2` alias; added through `&{/aliases}`.
5. Baud-rate accuracy of `owl-uart` at 115200 (it sets the UART clock to
   8 x baud) is not known.
6. SC16IS752 interrupt as `IRQ_TYPE_LEVEL_LOW` on the S900 GPIO controller.
7. `ttySC0` / `ttySC1` and `pps0` numbering assume no other such devices.
8. EMC2301: push-pull PWM, 26 kHz, normal polarity, low-side switching of a
   3-wire fan; the tach reading may be unusable below 100 % duty.
9. BQ25895 charge values (4.208 V, 3.008 A, 256 mA termination and
   pre-charge) are placeholders to be set for the fitted cells. The driver
   turns the chip watchdog off, so they persist while the host is off.
10. MAX17048 has no interrupt: it shares GPIO-D with the charger and neither
    driver requests a shared IRQ. Its low-SOC alert is unused.
11. `gpio-keys` on a 20-44 ms pulse with the emulated both-edge interrupt of
    `pinctrl-owl`.
12. `gpio-poweroff` (JP2 2-3): PS_HOLD must be high within the STM6601
    tON_BLANK (5.6 s min); the kernel driver probes too late for that unless
    the boot loader drives GPIO-F or C142/R124 are fitted. Interaction with
    an existing PMIC power-off handler in the user's kernel is unknown.
13. Default power-off path (JP2 1-2) depends on the PMIC dropping +1V8 at
    shutdown, and on +1V8 rising within tON_BLANK at power-on (study 16.10).
    Neither is a software matter, both are unmeasured.

GPIO (`gpio/`)

14. Needs `CONFIG_GPIO_SYSFS` (+ `CONFIG_GPIO_SYSFS_LEGACY` where it exists).
    The chip is found through `gpiochipN/device/of_node/compatible`; that
    sysfs path is assumed.
15. Assumes `stm32flash` leaves already-exported GPIOs exported.

MMDVM (`mmdvm/`)

16. `MMDVM.ini` placeholders: `Callsign=N0CALL`, `Id=1234567`,
    `RXFrequency=0`, `TXFrequency=0`, `ColorCode=1`. The unit refuses to
    start with `N0CALL`. Behaviour of the firmware with frequency 0 was not
    checked.
17. `[DMR Network] Enable=0`: no gateway (DMRGateway etc.) is installed by
    this package, so the hotspot is RF-only until one is added.
18. Display path (`Port=modem` -> MQTT -> MMDVM-Host -> STM32 USART2 -> TJC)
    is taken from the upstream sources; never seen working with a TJC X5.
    No 800x480 TJC screen file exists. MMDVM-Info is not installed.
19. `build.sh` dependency list comes from the upstream Makefiles and
    includes; not built on arm64 here.
20. Flashing: 8E1 on `ttyOWL2`, GPIO sequence copied from the firmware's
    Raspberry Pi script.

Fan (`fan/`)

21. Curve values (30 / 33 / 45 degC, PWM 90..255, 150 while charging) are
    guesses. The TMP102 measures outlet air, not the SoC.
22. Power-supply name glob `*bq25890*` for the charging state is assumed.

GPS (`gps/`)

23. The host cannot configure the GPS (receive only). Baud rate (9600) and
    the NMEA sentences depend on what the Meshtastic firmware sets.
24. gpsd option `-s 9600`: assumed available in Ubuntu 24.04's gpsd.
25. chrony `offset 0.2` for NMEA is a guess; needs calibration. Ubuntu's
    AppArmor profile for chrony is assumed to allow `/dev/pps0`.
26. No GPS data while the GPS switch is off, Meshtastic is shut down, or
    (possibly) while Meshtastic power-saves the receiver.

Meshtastic (`meshtastic/`)

27. First provisioning cannot use `/dev/ttySC0` (the serial module is what
    enables that link); USB (J43) or BLE is required once.
28. `--gps-always-on` (`position.gps_update_interval 5`) is an unverified
    guess at keeping the receiver powered.
29. Serial module pins 19 / 20 at 115200 are taken from study 10.2 / 10.3.
30. The GPS-switch watcher service of study 3.3 is not implemented.

Network (`network/`)

31. USB host on the S900 is not in mainline; the LAN7500 depends on the
    user's kernel patches and on the high-speed-connector USB port working.
32. The `.link` file matches by driver (`smsc75xx`), i.e. any LAN75xx adapter.
    With a blank EEPROM (U64) the MAC address is random at every boot until
    `MACAddress=` is set or the EEPROM is programmed.
33. No renderer is set in the netplan file.

Not provided at all

34. Low-battery shutdown from the MAX17048 reading (study 4.5), lowering the
    charge voltage to 4.1 V for permanent mains use, INA226 logging,
    DMRGateway / YSFGateway with `USE_GPSD`, MMDVM-Info.

## Hardware observations made while writing this

These are about `hardware/` and `docs/`, which this package does not modify.

- **Floating inputs on GPIO-A, -B, -G: fixed in the hardware after this
  package was written** (R57 100k to GND on GPIO-A, R58 / R59 100k to
  +1V8_HOST on GPIO-B / -G). The original finding, for the record: U22
  (BOOT0 level shifter), U23 (STM32 NRST buffer) and U26 (RAK4630 reset
  buffer) took their inputs directly from host GPIOs with no pull resistor. From host power-up
  until `mmdvm-gpio init` runs, those inputs are undefined unless the S900
  pads have internal pulls (not checked). Possible effects: STM32 held in
  reset or started in the boot loader, and the always-on RAK4630 being reset
  while the host boots. A pull-down on LS_GPIO_A and pull-ups (to +1V8_HOST)
  on LS_GPIO_B and LS_GPIO_G would remove the dependency on software.
- **Fan controller**: the study text named an AMC6821; it has since been
  corrected to the EMC2301 + TMP102 of the schematic and BOM.
- **Charger INT and gauge ALRT share GPIO-D**; the mainline drivers cannot
  share that interrupt.
- **Ethernet EEPROM**: study 11.5 / 13.2 say "no EEPROM"; the schematic has
  U64 (93LC66A), added later (section 14).
- **Study 11.1** still names the `r8152` / `smsc95xx` drivers; the fitted
  LAN7500 uses `smsc75xx` (13.2 is correct).
- **Pin mapping**: no disagreement found between study 3.4, the hardware
  manual and the mainline device tree.

## Sources

- Bubblegum-96 hardware manual V1.1, section 5:
  <https://github.com/96boards/documentation/tree/master/consumer/bubblegum-96/hardware-docs>
- Mainline `arch/arm64/boot/dts/actions/s900-bubblegum-96.dts`, `s900.dtsi`,
  `drivers/pinctrl/actions/pinctrl-s900.c`, `drivers/tty/serial/owl-uart.c`,
  and the binding files cited in the overlay (torvalds/linux master,
  2026-11-16).
- <https://github.com/g4klx/MMDVM-Host> (`MMDVM-Host.ini`, `Makefile`),
  <https://github.com/g4klx/MMDVM-Display> (`MMDVM-Display.ini`, `README.md`).
- <https://github.com/juribeparada/MMDVM_HS> (`configs/MMDVM_HS_Dual_Hat.h`,
  `README.md`, `scripts/install_fw_hsdualhat.sh`).
- <https://github.com/meshtastic/protobufs> (`module_config.proto`).
