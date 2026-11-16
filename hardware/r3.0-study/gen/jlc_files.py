"""JLCPCB assembly files from the KiCad placement file and the BOM (any python 3).

  production/CPL_JLCPCB.csv   Designator, Mid X, Mid Y, Layer, Rotation (JLCPCB column names)
  production/BOM_JLCPCB.csv   the assembly BOM without the parts of jlc_exclude.csv
  production/hand_solder.csv  those parts, with the reason
  production/check_orientation.csv   the parts whose orientation matters, for the placement preview

Rotation: top-side angles are KiCad's; bottom-side angles are mirrored, (180 - angle) mod 360, as JLCPCB views
the bottom side from below. No per-package corrections are applied: the published correction tables were made
for older footprint libraries and a wrong correction is worse than none. Order with "Confirm Parts Placement"
and compare check_orientation.csv with the preview.

Usage: python jlc_files.py [front_panel]     (after make_production.sh has written the KiCad placement file;
       with `front_panel` the files of ../front_panel are written instead)
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
FP = len(sys.argv) > 1 and sys.argv[1] == 'front_panel'
PRJ = os.path.join(HERE, '..', 'front_panel') if FP else os.path.join(HERE, '..')
OUT = os.path.join(PRJ, 'production')
skip = {} if FP else {r['Reference']: r['Reason'] for r in csv.DictReader(open(os.path.join(HERE, 'jlc_exclude.csv'), encoding='utf-8'))}
pos = list(csv.DictReader(open(os.path.join(OUT, ('front_panel' if FP else 'mmdvm_mesh') + '-pos.csv'), encoding='utf-8')))
bom = list(csv.DictReader(open(os.path.join(PRJ, 'BOM.csv'), encoding='utf-8-sig')))
inbom = {ref: r for r in bom for ref in r['Reference'].split(',')}
n = 0
with open(os.path.join(OUT, 'CPL_JLCPCB.csv'), 'w', newline='', encoding='utf-8') as f, \
        open(os.path.join(OUT, 'check_orientation.csv'), 'w', newline='', encoding='utf-8') as g:
    w, c = csv.writer(f), csv.writer(g)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    c.writerow(['Designator', 'Value', 'Package', 'Layer', 'KiCad angle', 'CPL angle'])
    for p in pos:
        ref = p['Ref']
        if ref in skip or ref not in inbom:
            continue
        rot = float(p['Rot']) % 360
        bottom = p['Side'] == 'bottom'
        out = (180 - rot) % 360 if bottom else rot
        w.writerow([ref, '%.4fmm' % float(p['PosX']), '%.4fmm' % float(p['PosY']), 'Bottom' if bottom else 'Top', '%g' % out])
        n += 1
        if not re.match(r'^[RCL]\d', ref) or 'Elec' in p['Package'] or 'Tantal' in p['Package']:
            c.writerow([ref, p['Val'], p['Package'], 'Bottom' if bottom else 'Top', '%g' % rot, '%g' % out])
with open(os.path.join(OUT, 'BOM_JLCPCB.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    lines = 0
    for r in bom:
        refs = [x for x in r['Reference'].split(',') if x not in skip]
        if refs:
            w.writerow([r['MPN'] or r['Value'], ','.join(refs), r['Footprint'].split(':')[-1], r['LCSC']])
            lines += 1
with open(os.path.join(OUT, 'hand_solder.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Value', 'MPN', 'Mouser', 'Reason'])
    for ref, why in skip.items():
        r = inbom.get(ref, {})
        w.writerow([ref, r.get('Value', ''), r.get('MPN', ''), r.get('Mouser', ''), why])
placed = {p['Ref'] for p in pos}
nopos = sorted(ref for ref in inbom if ref not in placed and ref not in skip)
print('CPL: %d parts, BOM: %d lines, by hand: %d parts' % (n, lines, len(skip)))
if nopos:
    print('in the BOM but not in the placement file (through-hole parts are listed there only if KiCad exports them):', ', '.join(nopos))
