"""Connect GND pads the pours do not reach: drop a via to the In1 ground plane next to each one.

Usage: python stitch_gnd.py <drc.json>   (json from `kicad-cli pcb drc --format json`)
"""
import json
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
drc = json.load(open(sys.argv[1], encoding='utf-8'))
mm = pcbnew.FromMM
gnd = board.FindNet('GND')
pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
VIA_D, VIA_DR, W, CL = 0.45, 0.2, 0.2, 0.15


def _pip(px, py):
    hit = False
    poly = M.OUTLINE
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def inside(x, y):
    px, py = x - M.X0, M.Y0 - y
    return all(_pip(px + dx, py + dy) for dx in (-0.7, 0, 0.7) for dy in (-0.7, 0, 0.7))


def blocked(q, radius, layer=None):
    acc = mm(radius + CL)
    for p in pads:
        if p.GetNetname() != 'GND' and (layer is None or p.IsOnLayer(layer) or p.GetAttribute() in
                                        (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)) and p.HitTest(q, acc):
            return True
    for t in board.GetTracks():
        if t.GetNetname() == 'GND':
            continue
        if t.GetClass() == 'PCB_VIA' or layer is None or t.GetLayer() == layer:
            if t.HitTest(q, acc):
                return True
    return False


for z in board.Zones():
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
todo = []
for it in drc['unconnected_items']:
    for i in it['items']:
        if '[GND]' in i['description']:
            q = pcbnew.VECTOR2I(mm(i['pos']['x']), mm(i['pos']['y']))
            for p in pads:
                if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.HitTest(q, mm(0.05)):
                    if p not in todo:
                        todo.append(p)
done = fail = 0
for p in todo:
    c = p.GetPosition()
    layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    ok = False
    for r in (0.6, 0.75, 0.9, 1.1, 1.4, 1.8, 2.3, 2.9, 3.6):
        for k in range(16):
            a = 2 * math.pi * k / 16
            x, y = c.x + mm(r * math.cos(a)), c.y + mm(r * math.sin(a))
            v = pcbnew.VECTOR2I(int(x), int(y))
            if not inside(pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)) or blocked(v, VIA_D / 2):
                continue
            n = max(2, int(r / 0.1))
            if any(blocked(pcbnew.VECTOR2I(int(c.x + (v.x - c.x) * j / n), int(c.y + (v.y - c.y) * j / n)), W / 2, layer)
                   for j in range(1, n + 1)):
                continue
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(v); via.SetWidth(mm(VIA_D)); via.SetDrill(mm(VIA_DR)); via.SetNet(gnd)
            board.Add(via)
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(c); t.SetEnd(v); t.SetWidth(mm(W)); t.SetLayer(layer); t.SetNet(gnd)
            board.Add(t)
            ok = True
            break
        if ok:
            break
    done += ok
    fail += not ok
    if not ok:
        print('no room near', p.GetParentFootprint().GetReference(), p.GetNumber())
# isolated pour islands on the outer layers (they carry GND pads): drop a via inside each island that has
# no GND via / plated hole yet
isl = noroom = 0
anchors = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND']
anchors += [p.GetPosition() for p in pads if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
for z in board.Zones():
    layer = z.GetLayer()
    if layer not in (pcbnew.F_Cu, pcbnew.B_Cu):
        continue
    ps = z.GetFilledPolysList(layer)
    for i in range(ps.OutlineCount()):
        if any(ps.Contains(a, i) for a in anchors):
            continue
        bb = ps.Outline(i).BBox()
        ok = False
        step = mm(0.15)
        y = bb.GetY()
        while y <= bb.GetY() + bb.GetHeight() and not ok:
            x = bb.GetX()
            while x <= bb.GetX() + bb.GetWidth():
                v = pcbnew.VECTOR2I(int(x), int(y))
                d = mm(VIA_D / 2 + 0.05)
                if ps.Contains(v, i) and inside(pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)) and not blocked(v, VIA_D / 2)                         and not any(p.HitTest(v, mm(0.05)) for p in pads):
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(v); via.SetWidth(mm(VIA_D)); via.SetDrill(mm(VIA_DR)); via.SetNet(gnd)
                    board.Add(via)
                    anchors.append(v)
                    isl += 1
                    ok = True
                    break
                x += step
            y += step
        noroom += not ok
print('islands without room for a via', noroom)
print('island vias', isl)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('GND pads stitched', done, 'failed', fail)
sys.stdout.flush()
os._exit(0)
