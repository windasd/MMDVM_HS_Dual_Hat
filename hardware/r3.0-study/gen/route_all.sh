#!/bin/bash
# Full routing pipeline for the r3.0 main board. Run from hardware/r3.0-study/gen after main_pcb.py.
#   JAVA=<java 17+>  FREEROUTING=<freerouting-1.9.0.jar>  KPY=<KiCad python>  bash route_all.sh
#
# This script only covers the first autorouter pass. The board in the repository went through more steps
# afterwards, each made on the routed board (the routed board is the master, main_pcb.py refuses to
# overwrite it without --force):
#   pair_route.py / pair_tails.py / usb_ref_plane.py   differential pairs and their reference strip
#   eth_pour.py, rf_lines.py                           +1V2_ETH pour, 50 ohm antenna feeds
#   power_layout.py place | rip | copper | lock        power section re-placed, wide copper
#   vbus_path.py place | rip | copper                  wide VBUS, C102 at the charger
#   via_out_of_pad.py --locked                         vias off SMD pads
#   hand_edit.py hand_edits.txt                        the edits no tool could make (a record, not replayable
#                                                      on a different routing)
#   tidy_silk.py, snapshot_placement.py                silk, then placement.json for main_pcb.py
# with reroute_prep.py + Freerouting (fill the gaps), patch_route.py and the DRC in between.
# After any change: power_paths.py, via_out_of_pad.py --dry --locked, kicad-cli pcb drc, make_production.sh.
set -e
KPY="${KPY:-/c/Program Files/KiCad/10.0/bin/python.exe}"
KCLI="${KCLI:-/c/Program Files/KiCad/10.0/bin/kicad-cli.exe}"
: "${JAVA:?set JAVA to a Java 17+ binary}"; : "${FREEROUTING:?set FREEROUTING to freerouting-1.9.0.jar}"
cd "$(dirname "$0")"
PRO=../mmdvm_mesh.kicad_pro; cp "$PRO" ../route_pro.bak 2>/dev/null || true
# CONTINUE=1: keep the existing routing, lock only the tracks of ../route/placed.kicad_pcb (the r1.3 block)
# and let the router rip up and retry the rest.
REF=../route/placed.kicad_pcb; mkdir -p ../route
if [ -z "$CONTINUE" ]; then cp ../mmdvm_mesh.kicad_pcb "$REF"; PREP_ARG=""; else PREP_ARG="$REF"; fi
drc() { cp ../route_pro.bak "$PRO"; "$KCLI" pcb drc --schematic-parity --severity-all --format json -o ../route/drc.json ../mmdvm_mesh.kicad_pcb >/dev/null 2>&1 || true; }
q() { grep -v -E "image handler|memory leak"; }
"$KPY" reroute_prep.py $PREP_ARG 2>&1 | q
(cd ../route && rm -f mmdvm_mesh.ses && "$JAVA" -jar "$FREEROUTING" -de mmdvm_mesh.dsn -do mmdvm_mesh.ses -mp 40 > fr.log 2>&1)
"$KPY" route.py import 2>&1 | q
drc; "$KPY" stitch_gnd.py ../route/drc.json 2>&1 | q | tail -3
drc; "$KPY" bridge_gaps.py ../route/drc.json 2>&1 | q | tail -3
"$KPY" widen_power.py 2>&1 | q | tail -2
drc; "$KPY" stitch_gnd.py ../route/drc.json --via-in-pad 2>&1 | q | tail -12
"$KPY" relock.py "$REF" 2>&1 | q
drc; cp ../route_pro.bak "$PRO"; rm -f ../route_pro.bak
"$KPY" -c "
import json; from collections import Counter
d=json.load(open('../route/drc.json',encoding='utf-8'))
print('unconnected',len(d['unconnected_items']),'parity',len(d['schematic_parity']))
print([k for k in Counter((x['severity'],x['type']) for x in d['violations']).most_common() if 'silk' not in k[0][1]])
for x in d['unconnected_items']:
    ds=[i['description'][:48] for i in x['items']]
    if not all('GND' in s for s in ds): print('  open:',ds)"
