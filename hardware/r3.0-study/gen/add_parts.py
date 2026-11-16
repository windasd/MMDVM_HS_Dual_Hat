"""Add footprints for symbols that are new in the schematic to the routed board, and re-net changed pads.

For small schematic changes where re-placing and re-routing the whole board (main_pcb.py) is not wanted.
Run sync_pcb.py afterwards, then rip / route the affected connections (patch_route.py).

Usage: python add_parts.py REF:x,y,rot [...]      (board coordinates in mm, as shown in the PCB editor)
"""
import os
import sys

import pcbnew

import main_pcb as M

comps, pins = M.netlist()
PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)


def net(name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        print('new net', name)
    return n


for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        n = pins.get((ref, pad.GetNumber()))
        if n and pad.GetNetname() != n:
            print('re-net %s.%s: %s -> %s' % (ref, pad.GetNumber(), pad.GetNetname(), n))
            pad.SetNet(net(n))
for a in sys.argv[1:]:
    ref, xyz = a.split(':')
    x, y, rot = (float(v) for v in xyz.split(','))
    if board.FindFootprintByReference(ref):
        print(ref, 'is already on the board')
        continue
    c = comps[ref]
    fp = M.load_fp(c['fp'])
    fp.SetParent(board)
    fp.SetReference(ref)
    fp.SetValue(c['val'])
    fp.SetFPIDAsString(c['fp'])
    fp.SetPath(pcbnew.KIID_PATH(c['path']))
    fp.SetSheetname(c['sheet'])
    if c['dnp']:
        fp.SetDNP(True)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    for pad in fp.Pads():
        n = pins.get((ref, pad.GetNumber()))
        if n:
            pad.SetNet(net(n))
    print('added', ref, c['fp'], [(p.GetNumber(), p.GetNetname()) for p in fp.Pads()])
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
