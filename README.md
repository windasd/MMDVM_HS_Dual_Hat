# MMDVM_HS_Dual_Hat
Duplex variant of MMDVM_HS_Hat
DB9MAT DF2ET DO7EN

This PCB uses the [MMDVM_HS](https://github.com/juribeparada/MMDVM_HS) by Andy CA6JAU. It has two ADF7021 onboard and allows for duplex operation with two time slots on DMR.

![MMDVM_HS_Dual_Hat](https://github.com/phl0/MMDVM_HS_Dual_Hat/blob/master/mmdvm_hs_dual_hat.png)

## Revisions

### Revision 1.0

Initial release.

### Revision 1.1

LEDs D4 and D5 interchanged to align with scan order. Solder jumper JP1 was added. It can be closed if the board is used on Raspberry Pi only. It ties BOOT1 to GND. BOOT0 is controlled via GPIO. The 2x3 pin header can be unpopulated in this case to save space. We placed two coils on U1 and U2 for experiments with extended VCO. These are L11 and L12 and they are optional and do not need to be inserted for UHF use. Testpoints TP1 and TP2 on backside allows the demodulator output SNR to be measured with #define TEST_DAC compiled firmware.

**This version is not recommended for (re-)production!**

### Revision 1.2

An accidentially deleted 3v3 wire has been added back to the PCB layout. BOM, Mouser cart and stencil stay the same as for rev1.1.

### Revision 1.3

STlink header has been refactored to have the same pinout as the [MMDVM_HS_Hat](https://github.com/mathisschmieder/MMDVM_HS_Hat) boards. OLED and STlink header have been exchanged. JP1 has been slightly moved. C44, C45 and C46 have been relocated nearer to the STM32F1 CPU. A table was added to the bottom silkscreen to show which TCXO is installed. This is important to the firmware. BOM and Mouser cart are still the same. The stencil has slightly changed. If you manually solder C44-C46 you can still use the old one.

### Revision 2.0 mini

Fully reworked 4-layer layout in Raspberry Pi Zero form factor (65 x 30 mm) with on-board ceramic chip antennas instead of SMA connectors. The project files are in `hardware/r2.0-mini`, its BOM in `hardware/r2.0-mini/BOM.csv`.

**Antenna note:** the chip antenna footprint/3D model used in the layout is the Yageo ANT1204LL08R0870A, which is an 870 MHz part. The BOM now lists the 433 MHz variant ANT1204LL20R0433A (same 12 x 4 mm body and land pattern). On-board chip antennas always need a matching network tuned on the real board; expect to retune for the 70 cm band.

## KiCad 10 migration (2026)

Both revisions have been migrated to KiCad 10 (KiCad 10.0 or newer is required to open them).

* All symbols and footprints link to the KiCad 10 standard libraries or to the shared project libraries in `libraries/` (`mmdvm_hs_dual_hat.kicad_sym`, `mmdvm_hs_dual_hat.pretty`). The "rescue" and cache libraries are gone.
* Symbols whose pin geometry differs from the KiCad 10 standard symbols (STM32F103C8Tx, ADF7021, Raspberry Pi header, CONN_*, USB_OTG, LD1117S33TR, GS2, antenna, NC/NO jumper) were moved unchanged into the project symbol library, so no wires had to be redrawn.
* Footprints were replaced by their KiCad 10 standard equivalents where the pad geometry matches closely and DRC shows no new violation. Parts where the newer, larger pads would violate the existing clearances keep their original geometry from the project library: rev1.3 U1, U2, U3, R15, R16, C4, C17, C18, C33, C39 and rev2.0-mini U1, U2 (thermal vias). rev2.0-mini R15, U4, P3, P4, J2, J4 keep their `pkl` footprints.
* **rev1.3 schematic fix:** the schematic redraw from 2020 left the STM32 VSS/VSSA pins (8, 23, 35, 47) unconnected, drew the TCXO X1 with VDD and GND swapped, and swapped OSC_IN/OSC_OUT. The PCB itself was always correct. The schematic has been repaired to match the PCB and the original 2018 netlist again; running "Update PCB from Schematic" on the old schematic would have reverse-powered the TCXO.
* Schematic and PCB are in sync (net names, footprints, fields).
* ERC: PWR_FLAGs added for GND, +5V, +3V3 (rev1.3) and GND, +5V, regulator input (rev2.0-mini); ADF7021 pin 33 (SWD, sync word detect) is now an output. Only rev2.0-mini keeps four isolated-label warnings (SWD_TP1/2, D+/D-: signal names left from rev1.3).
* DRC rev2.0-mini: J2/J4 solder jumpers are now net-tie footprints (pads 1-2 bridged by design) with solder mask bridges allowed, chip antenna silkscreen no longer overlaps the pads, a dangling track stub was removed. rev1.3: two 10 µm track slivers removed.
* Remaining, reviewed DRC items: rev1.3 courtyard overlaps (C44/C45 at the MCU, stitching via at U4, mounting hole at J1), two single-spoke thermal reliefs, rev2.0-mini two silkscreen clearance warnings, and silkscreen text below 0.8 mm on both boards.
* rev2.0-mini needs the `libraries/pkl` submodule: clone with `git clone --recursive` or run `git submodule update --init`.

## BOM

`BOM.csv` / `BOM.xlsx` in the repository root are for rev1.3, `hardware/r2.0-mini/BOM.csv` / `BOM.xlsx` for rev2.0-mini. Both are exported from the schematics.

Part availability was checked in November 2026. Changes against the original BOM:

| Ref | Old part | New part | Reason |
|---|---|---|---|
| 100n caps | Vishay VJ0402V104ZXJCW1BC (Y5V) | Murata GCM155R71C104KA55D (X7R) | obsolete |
| C52 (rev1.3) | Murata GRM155C80J106ME11J | Murata GRT155C80J106ME13D | discontinued |
| C52 (rev2.0-mini) | 0402 part on an 0603 footprint | Samsung CL10A106KP8NNNC (10 V) | wrong size |
| C33, C34 | AVX 04025A220GAT2A | Kyocera AVX KGM05ACG1H220GH | new part number, same part |
| C47, C48 | Murata GRM1555C1H470FA01D | Murata GJM1555C1H470FB01D | NRND |
| C51 | AVX TPSA106K010T0900 | Kyocera AVX TPSA106K010R0900 | same spec, in stock |
| R3, R4 | Susumu RR0510P-3831-D | Panasonic ERA-2AEB3831X | not stocked, 0.1 % instead of 0.5 % |
| P1, P2 | TE 5-1814832-1 | TE 5-1814832-2 | superseded; same drawing 1814832 rev C, only the packaging differs (tape & reel) |
| L9, L10 | value "100MHz" / "10u" | value "70R@100MHz" | Würth 74279277 is a ferrite bead, the MPN was right |
| rev2.0-mini U3, U4, J1, A1, A2 | no part number | STM32F103C8T6, TLV70233DBVR, Harwin M20-7832046, ANT1204LL20R0433A | missing |

Empty `SPN` fields mean the Mouser part number could not be verified (Mouser blocks automated lookups); search Mouser by the MPN. Parts with thin stock at the time of checking: TE 36501E20NJTDG (L3, L4; alternative Murata LQW15AN20NG80D, re-check the RF match), Murata GCM1555C1H471JA16J (C21, C22; alternative GRT1555C1H471JA02D), Panasonic ERA-2AEB271X (R9, R10). For 12.288 MHz boards use ECS-TXO-3225-122.8-TR for X1.

## Production files

`kicad-cli` exports Gerber X2/Excellon, drill maps, placement CSV, BOM and schematic PDF to `hardware/<rev>/production/` (not tracked in git, see `FAB_NOTES.md` there for board specs). rev1.3 needs a new stencil because the 0402 pads changed; rev2.0-mini has one SMD part (A1) on the bottom side.

The old Mouser carts below are for rev1.0/rev1.1 and still contain the obsolete parts.

Mouser cart for rev1.0 is [here](https://www.mouser.com/ProjectManager/ProjectDetail.aspx?AccessID=561bb01347).

[This](https://www.mouser.com/ProjectManager/ProjectDetail.aspx?AccessID=24ea9d644e) is the Mouser cart for rev1.1. L11 and L12 are optional.

## Firmware installation

The device can be used on top on a RPi attached via the GPIO port or standalone and connected via USB. Both variants require different handling of compiling and uploading the firmware. The USB connection requires firmware with bootloader support whereas the GPIO version does not. 

For USB connection a bootloader has to be installed initally. This requires STlink connection. After that is done the MMDVM_HS firmware upgrade can be done via the USB connection. The STlink connection can be used as fallback if wrongly configured firmware was installed for example.

### Install the firmware with bootloader support for USB connection

If you want to use the device via USB port you have to install a bootloader and build the firmware with bootloader support. As the raw device cannot be used with USB you have to use a USB-serial adapter or STlink device. Using STlink this can be done as follows:

```
user@host:/opt/MMDVM_HS$ make stlink-bl 
././STM32F10X_Lib/utils/linux64/st-flash write ./STM32F10X_Lib/utils/bootloader/generic_boot20_pc13.bin 0x8000000
2018-03-02T10:01:04 INFO src/usb.c: -- exit_dfu_mode
2018-03-02T10:01:04 INFO src/common.c: Loading device parameters....
2018-03-02T10:01:04 INFO src/common.c: Device connected is: F1 Medium-density device, id 0x20036410
2018-03-02T10:01:04 INFO src/common.c: SRAM size: 0x5000 bytes (20 KiB), Flash: 0x10000 bytes (64 KiB) in pages of 1024 bytes
2018-03-02T10:01:04 INFO src/common.c: Attempting to write 7160 (0x1bf8) bytes to stm32 address: 134217728 (0x8000000)
Flash page at addr: 0x08001800 erased
2018-03-02T10:01:04 INFO src/common.c: Finished erasing 7 pages of 1024 (0x400) bytes
2018-03-02T10:01:04 INFO src/common.c: Starting Flash write for VL/F0/F3 core id
2018-03-02T10:01:04 INFO src/common.c: Successfully loaded flash loader in sram
  6/6 pages written
2018-03-02T10:01:05 INFO src/common.c: Starting verification of write complete
2018-03-02T10:01:05 INFO src/common.c: Flash written and verified! jolly good!
././STM32F10X_Lib/utils/linux64/st-flash write bin/mmdvm_f1bl.bin 0x8002000
2018-03-02T10:01:05 INFO src/common.c: Loading device parameters....
2018-03-02T10:01:05 INFO src/common.c: Device connected is: F1 Medium-density device, id 0x20036410
2018-03-02T10:01:05 INFO src/common.c: SRAM size: 0x5000 bytes (20 KiB), Flash: 0x10000 bytes (64 KiB) in pages of 1024 bytes
2018-03-02T10:01:05 INFO src/common.c: Attempting to write 55016 (0xd6e8) bytes to stm32 address: 134225920 (0x8002000)
Flash page at addr: 0x0800f400 erased
2018-03-02T10:01:07 INFO src/common.c: Finished erasing 54 pages of 1024 (0x400) bytes
2018-03-02T10:01:07 INFO src/common.c: Starting Flash write for VL/F0/F3 core id
2018-03-02T10:01:07 INFO src/common.c: Successfully loaded flash loader in sram
 53/53 pages written
2018-03-02T10:01:12 INFO src/common.c: Starting verification of write complete
2018-03-02T10:01:13 INFO src/common.c: Flash written and verified! jolly good!
```

The device should now be usable as /dev/ttyACMx. 

If you want to update the MMDVM_HS firmware itself later on via USB you can use the dfu upload method. The settings in Config.h are:

    #define MMDVM_HS_DUAL_HAT_REV10
    #define ENABLE_ADF7021
    #define DUPLEX

    #define ADF7021_14_7456

or
    #define ADF7021_12_2880

for boards with 12.288MHz TCXO.

    #define STM32_USB_HOST
    #define ENABLE_SCAN_MODE

Optionally:

    #define SEND_RSSI_DATA
    #define SERIAL_REPEATER

Compile the firmware with "make bl" and then:

```
user@host:/opt/MMDVM_HS$ sudo make dfu devser=/dev/ttyACM3
././STM32F10X_Lib/utils/linux64/upload-reset /dev/ttyACM3 750
././STM32F10X_Lib/utils/linux64/dfu-util -D bin/mmdvm_f1bl.bin -d 1eaf:0003 -a 2 -R -R
dfu-util 0.7

Copyright 2005-2008 Weston Schmidt, Harald Welte and OpenMoko Inc.
Copyright 2010-2012 Tormod Volden and Stefan Schmidt
This program is Free Software and has ABSOLUTELY NO WARRANTY
Please report bugs to dfu-util@lists.gnumonks.org

Filter on vendor = 0x1eaf product = 0x0003
Opening DFU capable USB device... ID 1eaf:0003
Run-time device DFU version 0110
Found DFU: [1eaf:0003] devnum=0, cfg=1, intf=0, alt=2, name="STM32duino bootloader v1.0  Upload to Flash 0x8002000"
Claiming USB DFU Interface...
Setting Alternate Setting #2 ...
Determining device status: state = dfuIDLE, status = 0
dfuIDLE, continuing
DFU mode device DFU version 0110
Device returned transfer size 1024
No valid DFU suffix signature
Warning: File has no DFU suffix
bytes_per_hash=1100
Copying data from PC to DFU device
Starting download: [##################################################] finished!
state(8) = dfuMANIFEST-WAIT-RESET, status(0) = No error condition is present
Done!
Resetting USB to switch back to runtime mode
```

### Compile and upload manually for GPIO connection

For specific details about the firmware installation, check [these](https://github.com/juribeparada/MMDVM_HS#build-de-firmware-and-upload-to-zumspot-rpi) instructions. The process is similar to the installation on the ZumSpot Pi. You can make use of the preconfigured scripts in MMDVM_HS. Editing Config.h by hand requires these settings:

Enable the following settings in Config.h: 

    #define MMDVM_HS_DUAL_HAT_REV10
    #define ENABLE_ADF7021
    #define DUPLEX
    #define ADF7021_14_7456
    #define STM32_USART1_HOST
    #define ENABLE_SCAN_MODE

Optionally:

    #define SEND_RSSI_DATA
    #define SERIAL_REPEATER

And for 12.288MHz TCXO equipped boards

    #define ADF7021_12_2880

instead of the 14_7456 option.

Build the firmware:

    make

Make sure the two BOOT jumpers are set as follows:

    BOOT0: completey removed
    BOOT1: set to BOOT 1 -

And finally upload the firmware to the MMDVM_HS_Dual_Hat:

    sudo make mmdvm_hs_dual_hat

### Update within Pi-Star

[PiStar](http://www.pistar.uk/) contains a binary that allow for flashing precompiled binary firmware to the MMDVM_HS_Dual_Hat. To update the firmware within PiStar execute the following commands:

    $ rpi-rw
    $ pistar-mmdvmhshatflash hs_dual_hat

If you have a board equipped with 12.288MHz TCXO you have to flash the according firmware type using:

    $ pistar-mmdvmhshatflash hs_dual_hat-12mhz

## License
This project is released under the Creative Commons Attribution-NonCommercial-ShareAlike 3.0 (CC-BY-NC-SA 3.0, https://creativecommons.org/licenses/by-nc-sa/3.0/) license. You may edit and share it as you like, as long as credit is given and the license is not changed. You can build as many boards for you and your friends as you like and you can even sell it to them to cover your costs, **however it is strictly forbidden to turn this into a commercial product! You are not allowed to build and sell these boards for profit!**
