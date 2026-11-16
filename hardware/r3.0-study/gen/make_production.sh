#!/bin/bash
# Export the fabrication set of the main board to ../production (git-ignored): Gerbers, drill files,
# placement file, JLCPCB BOM, schematic PDF and a zip of the Gerber/drill folder.
# Run bom_export.py first so that BOM_JLCPCB.csv is current.
KC="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
KPY="/c/Program Files/KiCad/10.0/bin/python.exe"
cd "$(dirname "$0")/.." || exit 1
OUT=production
rm -rf "$OUT/gerber_drill" && mkdir -p "$OUT/gerber_drill"
"$KC" pcb export gerbers -o "$OUT/gerber_drill/" \
  -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask mmdvm_mesh.kicad_pcb | tail -1
"$KC" pcb export drill -o "$OUT/gerber_drill/" --format excellon --excellon-separate-th \
  --generate-map --map-format gerberx2 mmdvm_mesh.kicad_pcb | tail -1
"$KC" pcb export pos -o "$OUT/mmdvm_mesh-pos.csv" --format csv --units mm --side both --exclude-dnp mmdvm_mesh.kicad_pcb | tail -1
"$KC" sch export pdf -o "$OUT/mmdvm_mesh-schematic.pdf" mmdvm_mesh.kicad_sch | tail -1
cp BOM_JLCPCB.csv "$OUT/"
"$KPY" -c "
import os, zipfile
z = zipfile.ZipFile('$OUT/mmdvm_mesh-gerber.zip', 'w', zipfile.ZIP_DEFLATED)
for f in sorted(os.listdir('$OUT/gerber_drill')):
    z.write(os.path.join('$OUT/gerber_drill', f), f)
z.close(); print('zip:', len(z.namelist()), 'files')"
ls "$OUT/gerber_drill" | wc -l
