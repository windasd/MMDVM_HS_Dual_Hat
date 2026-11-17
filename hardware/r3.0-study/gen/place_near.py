"""Find a free spot for a small two-pad part near a point on the routed board and report it (KiCad python).

Usage: python place_near.py REF:x,y [REF:x,y ...]      prints "REF:x,y,rot" lines for add_parts.py
The part must exist in the schematic (its footprint is loaded the way add_parts.py does). A spot is free when
the pads keep 0.15 mm from all copper on F.Cu, from every via, and the courtyard clears the other courtyards.
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

comps, pins = M.netlist()
board = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb'))
mm, F = pcbnew.ToMM, pcbnew.FromMM


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0, p[0] - r[2]), max(r[1] - p[1], 0, p[1] - r[3]))


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


trk, via, pad, crt = [], [], [], []
for t in board.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        via.append((mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth(pcbnew.F_Cu)) / 2))
    elif t.GetLayer() == pcbnew.F_Cu:
        trk.append(((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2))
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            b = p.GetBoundingBox()
            pad.append((mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())))
    if not fp.IsFlipped():
        c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if c.GetWidth() > 0:
            crt.append((mm(c.GetLeft()), mm(c.GetTop()), mm(c.GetRight()), mm(c.GetBottom())))


def clear(r, gap):
    """A rectangle against the F.Cu copper."""
    pts = [(r[0] + (r[2] - r[0]) * i / 4, r[1] + (r[3] - r[1]) * j / 4) for i in range(5) for j in range(5)]
    for x, y, rad in via:
        if rect_d((x, y), r) < rad + gap:
            return False
    for a, e, hw in trk:
        if min(a[0], e[0]) - 1 > r[2] or max(a[0], e[0]) + 1 < r[0] or min(a[1], e[1]) - 1 > r[3] or max(a[1], e[1]) + 1 < r[1]:
            continue
        if any(seg_d(p, a, e) < hw + gap for p in pts) or rect_d(a, r) < hw + gap or rect_d(e, r) < hw + gap:
            return False
    for q in pad:
        if q[0] < r[2] + gap and r[0] < q[2] + gap and q[1] < r[3] + gap and r[1] < q[3] + gap:
            return False
    return True


for arg in sys.argv[1:]:
    ref, xy = arg.split(':')
    tx, ty = (float(v) for v in xy.split(','))
    fp = M.load_fp(comps[ref]['fp'])
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    cw, ch = mm(c.GetWidth()) / 2, mm(c.GetHeight()) / 2
    pr = [(mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetSize().x) / 2, mm(p.GetSize().y) / 2) for p in fp.Pads()]
    best = None
    cand = sorted(((dx * 0.1, dy * 0.1) for dx in range(-60, 61) for dy in range(-60, 61)), key=lambda d: math.hypot(*d))
    for dx, dy in cand:
        x, y = round(tx + dx, 2), round(ty + dy, 2)
        for rot in (0, 90):
            w, h = (cw, ch) if rot == 0 else (ch, cw)
            cy = (x - w, y - h, x + w, y + h)
            if any(q[0] < cy[2] and cy[0] < q[2] and q[1] < cy[3] and cy[1] < q[3] for q in crt):
                continue
            ok = True
            for px, py, sw, sh in pr:
                if rot == 90:
                    px, py, sw, sh = py, -px, sh, sw
                if not clear((x + px - sw, y + py - sh, x + px + sw, y + py + sh), 0.15):
                    ok = False
                    break
            if ok:
                best = (x, y, rot)
                break
        if best:
            break
    print('%s:%s' % (ref, '%g,%g,%d' % best if best else 'NO ROOM'), ' (%.1f mm from the target)' % math.hypot(best[0] - tx, best[1] - ty) if best else '')
sys.stdout.flush()
os._exit(0)
