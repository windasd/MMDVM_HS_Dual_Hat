"""Lock the tracks that also exist in a reference board (the r1.3 MMDVM block) and unlock the rest."""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')


def key(t):
    if t.GetClass() == 'PCB_VIA':
        return ('v', t.GetPosition().x, t.GetPosition().y)
    e = sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)])
    return (t.GetLayer(), e[0], e[1])


keep = {key(t) for t in pcbnew.LoadBoard(sys.argv[1]).GetTracks()}
board = pcbnew.LoadBoard(PCB)
n = 0
segs = vias = 0
for t in board.GetTracks():
    t.SetLocked(key(t) in keep)
    n += key(t) in keep
    vias += t.GetClass() == 'PCB_VIA'
    segs += t.GetClass() != 'PCB_VIA'
board.Save(PCB)
print('locked', n, 'of', len(keep), 'reference items | segments', segs, 'vias', vias)
sys.stdout.flush()
os._exit(0)
