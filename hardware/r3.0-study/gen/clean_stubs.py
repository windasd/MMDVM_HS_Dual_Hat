"""Remove dangling track stubs (and dangling vias) reported by DRC. Locked tracks (the r1.3 block) are kept.

Usage: python clean_stubs.py <drc.json>   (re-run DRC and repeat until 0 are removed)
"""
import json
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
drc = json.load(open(sys.argv[1], encoding='utf-8'))
mm = pcbnew.FromMM
tracks = list(board.GetTracks())
gone = kept = 0
dead = set()
for v in drc['violations']:
    if v['type'] not in ('track_dangling', 'via_dangling'):
        continue
    i = v['items'][0]
    q = pcbnew.VECTOR2I(mm(i['pos']['x']), mm(i['pos']['y']))
    want_via = v['type'] == 'via_dangling'
    for k, t in enumerate(tracks):
        if k in dead or (t.GetClass() == 'PCB_VIA') != want_via:
            continue
        if ('[' + t.GetNetname() + ']') in i['description'] and t.HitTest(q, mm(0.01)):
            if t.IsLocked():   # never touch the r1.3 block: its 'dangling' ends are live (removing them broke 19 nets)
                kept += 1
            else:
                dead.add(k)
                gone += 1
            break
for k in dead:
    board.Remove(tracks[k])
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('removed', gone, '| locked stubs left alone', kept)
sys.stdout.flush()
os._exit(0)
