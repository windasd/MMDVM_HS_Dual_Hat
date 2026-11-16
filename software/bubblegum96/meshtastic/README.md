# Meshtastic host link and STM32 flashing notes

Nothing here has been run on hardware.

## How the host talks to the RAK4630

| Host device | Path | Other end |
|---|---|---|
| `/dev/ttySC0` | SC16IS752 channel A (I2C 0x48 on LS I2C0) | nRF52840 P0.19 (RX) / P0.20 (TX): Meshtastic serial module, PROTO, 115200 |
| `/dev/ttySC1` | SC16IS752 channel B, receive only | GPS NMEA (used by gpsd, not by Meshtastic tools) |
| GPIO-G (LS pin 29) | U26, open drain | RAK4630 reset, low = reset: `mmdvm-gpio reset-mesh` |
| GPIO-I (LS pin 31) | U28 | GPS load-switch enable (slide switch AND 3V3_EN): `mmdvm-gpio gps-switch` |
| J43 (internal JST-SH) | nRF52840 USB | boot loader / UF2 / first provisioning; shows up as `/dev/ttyACM0` |

The channel-A baud rate is exact: 14.7456 MHz / 16 / 8 = 115200.

Install the CLI (Ubuntu 24.04 blocks `pip install` into the system Python):

```sh
sudo apt-get install -y pipx
pipx install meshtastic
pipx ensurepath
```

Use it (the user must be in the `dialout` group):

```sh
meshtastic --port /dev/ttySC0 --info
meshtastic --port /dev/ttySC0 --nodes
meshtastic --port /dev/ttySC0 --sendtext "hello"
```

## First boot (study section 10.3)

1. SWD (J42, pyOCD or J-Link), not from this host: UICR `REGOUT0`
   (0x10001304) = 3.3 V, `NFCPINS` (0x1000120C) = GPIO.
2. Flash the RAK4631 boot loader (`wiscore_rak4631_board_bootloader-0.4.4_s140_6.1.1`).
3. Copy `firmware-rak4631-*.uf2` through J43 (or BLE OTA).
4. Run `provision.sh` **over USB or BLE the first time**:
   `/dev/ttySC0` is dead until the serial module is enabled on P0.19/P0.20,
   so the settings that make the host link work cannot be sent over the
   host link.

   ```sh
   ./provision.sh --port /dev/ttyACM0        # J43 plugged into this computer
   ./provision.sh --dry-run                  # only print what would be sent
   ```

   It sets `lora.region TW`, `serial.enabled true`, `serial.mode PROTO`,
   `serial.rxd 19`, `serial.txd 20`, `serial.baud BAUD_115200`,
   `position.gps_mode ENABLED`. Optional: `--sh1106` (force the OLED type,
   study 10.4), `--gps-always-on` (unverified, see the script).

Not implemented: the study (section 3.3) describes a host service that
watches the GPS switch (GPIO-I) and resets the RAK4630 (GPIO-G) so the
firmware re-detects the GPS. It was left out because the firmware behaviour
it works around has not been observed yet. The manual equivalent is
`mmdvm-gpio gps-switch` followed by `mmdvm-gpio reset-mesh`.

## Flashing the STM32 (MMDVM_HS firmware)

Lines (study 3.1, schematic `host_if` sheet):

| Line | LS pin | S900 | Path | Polarity |
|---|---|---|---|---|
| BOOT0 | 23, GPIO-A | GPIOA0, line 0 | U22 (SN74LVC1T45) -> R25 10 k -> BOOT0 | high = boot loader |
| NRST | 24, GPIO-B | GPIOA1, line 1 | U23 (74LVC1G07, open drain) | low = reset |
| UART | 5 / 7 | UART2, `/dev/ttyOWL2` | U21 / U20 | STM32 USART1 (PA9/PA10) |

`../mmdvm/flash-mmdvm-hs.sh` wraps the steps below.

```sh
sudo apt-get install -y stm32flash          # not the i386 tools in the firmware repo
sudo systemctl stop mmdvmhost
B=$(sudo mmdvm-gpio number boot0)           # sysfs number = chip base + 0
R=$(sudo mmdvm-gpio number nrst)            # sysfs number = chip base + 1
sudo stm32flash -v -w mmdvm_hs_dual_hat_fw.bin -g 0x0 -R -i "$B,-$R,$R:-$B,$R" /dev/ttyOWL2
sudo mmdvm-gpio reset-modem
sudo systemctl start mmdvmhost
```

- The sequence is the one from the firmware's `install_fw_hsdualhat.sh`
  (`-i 20,-21,21:-20,21`), with this board's GPIO numbers.
- The sysfs numbers are not fixed: the S900 GPIO chip gets a dynamic base
  (512 or higher). `mmdvm-gpio` finds the chip by its device-tree compatible.
- `stm32flash -i` needs `CONFIG_GPIO_SYSFS` (see `../network/kernel-config.fragment`).
- The boot loader uses 8E1; `owl-uart` implements parity, so this should
  work, but it is untested.
- RTS/DTR sequences (`-i rts,-dtr...`) cannot be used: `owl-uart` does not
  drive modem-control outputs.
- Firmware: `mmdvm_hs_dual_hat_fw.bin` from the MMDVM_HS release (14.7456 MHz
  TCXO), or a build from `configs/MMDVM_HS_Dual_Hat.h`. For the 800x480 TJC
  screen the study recommends raising `SERIAL_REPEATER_BAUD`.
- Recovery if the firmware is broken: the ROM boot loader does not depend on
  the firmware, so the same command works; SWD is on P5.
