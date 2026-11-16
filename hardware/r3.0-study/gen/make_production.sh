#!/bin/bash
# Export the fabrication set to <project>/production (git-ignored): Gerbers, drill files, placement file,
# JLCPCB BOM and CPL (jlc_files.py), schematic PDF, FAB_NOTES.md and a zip of the Gerber/drill folder.
#   bash make_production.sh              main board
#   bash make_production.sh front_panel  front-panel board
# Run bom_export.py first so that BOM.csv is current.
KC="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
KPY="/c/Program Files/KiCad/10.0/bin/python.exe"
GEN="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = front_panel ]; then
  cd "$GEN/../front_panel" || exit 1; N=front_panel; LAYERS=F.Cu,B.Cu
else
  cd "$GEN/.." || exit 1; N=mmdvm_mesh; LAYERS=F.Cu,In1.Cu,In2.Cu,B.Cu
fi
OUT=production
rm -rf "$OUT/gerber_drill" && mkdir -p "$OUT/gerber_drill"
"$KC" pcb export gerbers -o "$OUT/gerber_drill/" \
  -l $LAYERS,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask $N.kicad_pcb | tail -1
"$KC" pcb export drill -o "$OUT/gerber_drill/" --format excellon --excellon-separate-th \
  --generate-map --map-format gerberx2 $N.kicad_pcb | tail -1
"$KC" pcb export pos -o "$OUT/$N-pos.csv" --format csv --units mm --side both --exclude-dnp $N.kicad_pcb | tail -1
"$KC" sch export pdf -o "$OUT/$N-schematic.pdf" $N.kicad_sch | tail -1
"$KPY" "$GEN/jlc_files.py" $1
[ -f FAB_NOTES.md ] && cp FAB_NOTES.md "$OUT/"
rm -f "$OUT/BOM.csv"
"$KPY" -c "
import os, zipfile
z = zipfile.ZipFile('$OUT/$N-gerber.zip', 'w', zipfile.ZIP_DEFLATED)
for f in sorted(os.listdir('$OUT/gerber_drill')):
    z.write(os.path.join('$OUT/gerber_drill', f), f)
z.close(); print('zip:', len(z.namelist()), 'files')"
ls "$OUT/gerber_drill" | wc -l
