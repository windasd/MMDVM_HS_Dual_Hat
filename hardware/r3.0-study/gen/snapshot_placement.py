"""Write the footprint placement of the routed board to placement.json (run with KiCad's python).

main_pcb.py applies this file after its own placement, so a regenerated board has every part where the
routed board has it (the power section, C102, C80, C115 and the other parts moved on the routed board).

Usage: python snapshot_placement.py
"""
import json
import os
import sys

import pcbnew

import main_pcb as M

board = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb'))
out = {}
for fp in board.GetFootprints():
    p = fp.GetPosition()
    out[fp.GetReference()] = [round(pcbnew.ToMM(p.x), 4), round(pcbnew.ToMM(p.y), 4),
                              round(fp.GetOrientationDegrees(), 2), 'B' if fp.IsFlipped() else 'F']
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'placement.json')
json.dump(out, open(path, 'w', encoding='utf-8'), indent=0, sort_keys=True)
print('placement of', len(out), 'footprints written to', path)
sys.stdout.flush()
os._exit(0)
