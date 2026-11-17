# MMDVM_HS_Dual_Hat r3.0 study – fabrication notes

Generated with KiCad 10.0.8 from `hardware/r3.0-study` (2026-11-16). Written for JLCPCB.

**This board has never been built.** It passes ERC / DRC and was checked against data sheets. Read
`docs/meshtastic-gps-study.md` section 16 (Traditional Chinese) before ordering; the open points are
repeated at the end of this file.

## PCB – main board (`mmdvm_mesh`)

| Item | Value |
|---|---|
| Size | 90.6 x 167.1 mm, L-shaped outline |
| Layers | 4 (F.Cu signal + GND pour, In1 GND plane, In2 signal + VSYS pour, B.Cu signal + GND pour) |
| Thickness | 1.6 mm, 1 oz outer / 0.5 oz inner |
| Stack-up | **JLC04161H-7628**, impedance control **yes** (select the stack-up on the order form) |
| Controlled lines | 50 ohm coplanar on F.Cu: 0.32 mm, 0.25 mm gap. 90 ohm pair on B.Cu: 0.235 / 0.145 mm. 100 ohm pairs on F.Cu: 0.20 / 0.14 mm (about 96 ohm) |
| Min. track / clearance | 0.15 mm (3 segments; otherwise 0.20 mm) / 0.10 mm |
| Vias | 0.45 / 0.20 mm (191), 0.50 / 0.25 mm (202), 0.50 / 0.30 mm (1), 0.60 / 0.30 mm (132), 0.60 / 0.40 mm (58); annular ring 0.125 mm on the two small sizes |
| Via covering | tented both sides. No via hole touches an SMD pad; plugged or filled vias are not needed |
| Min. PTH | 0.20 mm (thermal vias of U101), annular ring 0.15 mm on those and on the 0.5 mm pads – JLCPCB's absolute minimum, 0.20 mm is its recommendation |
| Plated slots | 0.6 x 1.4 and 0.6 x 1.7 mm (USB-C shell) |
| NPTH | 0.65 – 3.45 mm (locating pegs of connectors and cell holders); tracks, vias and pours keep 0.2 mm from them (rule in `mmdvm_mesh.kicad_dru`) |
| Copper to board edge | 0.3 mm or more |
| Solder mask / silkscreen | both sides |
| Surface finish | ENIG recommended (0.5 mm pitch QFN / LGA, RAK4630 castellations) |
| Fiducials | three per side (1 mm dot, 2 mm mask opening), FID1–FID6; not in the BOM or CPL |

Files: `production/gerber_drill/` (Gerber X2 + Excellon, PTH and NPTH separate, drill maps, `.gbrjob`);
upload `production/mmdvm_mesh-gerber.zip`. Regenerate with `bash gen/make_production.sh`.

## PCB – front panel (`front_panel/`)

26.1 x 20.1 mm, 2 layers, 1.6 mm, tracks 0.25 mm or wider, vias 0.6 / 0.3 mm, 2 x 2.7 mm mounting holes.
No impedance control. `bash gen/make_production.sh front_panel`.

## Assembly

* **Both sides carry SMD parts** (bottom: 8 x 0402 termination resistors, the two 96Boards connectors J1 / J10,
  the cell holders). Order double-sided assembly.
* `production/BOM_JLCPCB.csv` and `production/CPL_JLCPCB.csv` are in JLCPCB's format (365 parts, 144 lines).
  Unfitted parts (C142, R124, D20, SW2) are in neither file.
* **Not from JLCPCB** (`production/hand_solder.csv`): the four cell holders BT100–BT103 (Keystone 1042P) and
  the charger inductor L100 (Wurth 744316100) had no assembly stock on 2026-11-16. Buy and solder them by hand.
* **Check the stock on the day of the order:** `python gen/stock_check.py <boards>`. 115 of the 146 BOM lines
  are extended parts (a loading fee each). Thin on 2026-11-16: STM6601CM2DDM6F (23), J1 (10), RJ45 (21), X1 (7).
* **Part orientation:** the CPL angles of 56 parts come from comparing each KiCad footprint with the footprint
  in JLCPCB's own library, pad by pad (`gen/jlc_rotation.py`; 45 are turned, 11 already agree). 38 parts could
  not be decided that way and are marked CHECK in `production/check_orientation.csv`: LEDs and diodes (pad
  numbers of two-terminal parts are not a physical reference), the U.FL sockets, the RAK4630 and three other
  parts with no library footprint, the switches, the USB-C socket and the two bottom-side connectors. Tick
  "Confirm Parts Placement" and look at those in the preview.
* Through-hole parts in the BOM: J2, J5, P5, P7 (pin headers), J60 (RJ45), J100 (USB-C shell pins), SW101.
* The RJ45 (J60), the slide switches and the console header overhang the board edge.

## Reviewed and accepted

* `mmdvm_mesh.kicad_dru` waives three courtyard / silk checks (U3 with C44 / C45 as in rev1.3; Y3 beside SW101).
* The GPS switch is marked ON only and neither slide switch has a name on silk (no room at the board edge); the enclosure carries the labels.
* 106 reference designators are hidden on silk for lack of room.

## Not verified – read before ordering

* Nothing has been measured: power sequencing, charging, cell protection, Ethernet, RF.
* The host's 1.8 V start-up time is unknown. U111 (STM6601CM2D) waits 5.6 s; C142 / R124 are an unfitted
  fallback (design record 16.10).
* Q100 / Q101 are CSD16340Q3 on the generic NexFET 3.3 x 3.3 footprint; its land pattern was not compared
  with the "Q3" package drawing.
* The In2 ground strip under the USB pair is still crossed by 9 tracks (it was 29), in 7 places. Ground vias
  sit right beside most cuts (19 added; 7 of the 28 wanted spots had no room) so the return current steps to the
  In1 plane there. The 90 ohm figure assumes an unbroken reference.
* Two vias of the USB pair sit 0.12 mm from the pads of U60, under the package: the gap between the pad row and
  the exposed pad is 0.55 mm, so no standard via fits elsewhere. Tented; if in doubt order epoxy-filled vias.
* The VCO loop-filter node of U1 (rev1.3 RF section) is not the rev1.3 routing (9.3 mm, two vias, a short run on
  In2; U2 has 8.0 mm): check the 433 MHz spectrum.
* The enclosure (`case/meshtastic-concept`) has not been printed.
