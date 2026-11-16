"""Give every GND pad that sits on an isolated pour island its own via, even where tracks are in the way.

For each such pad the via position inside the pad with the fewest blocking track segments is chosen; those
segments (unlocked, other nets) are removed and the via is added locked. Afterwards run the router in
CONTINUE mode so it re-routes the removed pieces around the new vias.

Usage: python force_gnd.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
VIA_D, VIA_DR, CL = 0.45, 0.2, 0.1
gnd = board.FindNet('GND')
pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
tracks = list(board.GetTracks())
anchors = [t.GetPosition() for t in tracks if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND']
anchors += [p.GetPosition() for p in pads if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
todo = []
for z in board.Zones():
    layer = z.GetLayer()
    if layer not in (pcbnew.F_Cu, pcbnew.B_Cu) or z.GetNetname() != 'GND':
        continue
    ps = z.GetFilledPolysList(layer)
    for i in range(ps.OutlineCount()):
        if any(ps.Contains(a, i) for a in anchors):
            continue
        for p in pads:
            if p.GetNetname() == 'GND' and p.IsOnLayer(layer) and ps.Contains(p.GetPosition(), i, mm(0.3)):
                todo.append(p)
# GND SMD pads the pour does not touch at all (reported by DRC as pad <-> zone)
for ref, num in [a.split('.') for a in sys.argv[1:]]:
    todo += [p for p in pads if p.GetParentFootprint().GetReference() == ref and p.GetNumber() == num]
acc = mm(VIA_D / 2 + CL)
removed = added = 0
for p in todo:
    bb = p.GetBoundingBox()
    best = None
    y = bb.GetY() + mm(0.1)
    while y <= bb.GetY() + bb.GetHeight() - mm(0.1):
        x = bb.GetX() + mm(0.1)
        while x <= bb.GetX() + bb.GetWidth() - mm(0.1):
            q = pcbnew.VECTOR2I(int(x), int(y))
            if p.HitTest(q) and not any(o.GetNetname() != 'GND' and o.HitTest(q, acc) for o in pads):
                hit = [t for t in tracks if t.GetNetname() != 'GND' and t.HitTest(q, acc)]
                if not any(t.IsLocked() or t.GetClass() == 'PCB_VIA' for t in hit):
                    if best is None or len(hit) < len(best[1]):
                        best = (q, hit)
            x += mm(0.1)
        y += mm(0.1)
    name = '%s.%s' % (p.GetParentFootprint().GetReference(), p.GetNumber())
    if best is None:
        print('no position for', name)
        continue
    for t in best[1]:
        board.Remove(t)
        tracks.remove(t)
        removed += 1
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(best[0]); via.SetWidth(mm(VIA_D)); via.SetDrill(mm(VIA_DR)); via.SetNet(gnd)
    via.SetLocked(True)
    board.Add(via)
    added += 1
    print('via in pad', name, '| removed segments:', sorted({t.GetNetname() for t in best[1]}))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('vias added', added, 'segments removed', removed)
sys.stdout.flush()
os._exit(0)
