"""Add three optical fiducials per side to the routed board (KiCad python).

Each is KiCad's Fiducial_1mm_Mask2mm (1 mm copper dot in a 2 mm mask opening), placed at the free spot nearest
to three well-separated corners of the board: no copper of that side, no via and no courtyard within 1.6 mm,
1.5 mm or more from the board edge. They are board-only footprints (not in the schematic, BOM or CPL).

Usage: python add_fiducials.py
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm, F = pcbnew.ToMM, pcbnew.FromMM
POLY = [(M.X0 + x, M.Y0 - y) for x, y in M.OUTLINE]
R = 1.6


def inside(x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / float(y2 - y1):
            c = not c
    return c


def edge(x, y):
    d = 1e9
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        d = min(d, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return d


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0, p[0] - r[2]), max(r[1] - p[1], 0, p[1] - r[3]))


for fp in list(board.GetFootprints()):
    if fp.GetReference().startswith('FID'):
        board.Remove(fp)
done = []
for side, layer, crt in (('F', pcbnew.F_Cu, pcbnew.F_CrtYd), ('B', pcbnew.B_Cu, pcbnew.B_CrtYd)):
    trk = [((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2)
           for t in board.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetLayer() == layer]
    via = [(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth(layer)) / 2) for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
    rects = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) or p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                b = p.GetBoundingBox()
                rects.append((mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())))
        if fp.IsFlipped() == (side == 'B'):
            c = fp.GetCourtyard(crt).BBox()
            if c.GetWidth() > 0:
                rects.append((mm(c.GetLeft()), mm(c.GetTop()), mm(c.GetRight()), mm(c.GetBottom())))
    silk = pcbnew.F_SilkS if side == 'F' else pcbnew.B_SilkS
    for d in board.GetDrawings():
        if d.GetLayer() == silk:
            b = d.GetBoundingBox()
            rects.append((mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())))

    def free(x, y):
        if not inside(x, y) or edge(x, y) < 1.5 + 0.5:
            return False
        if any(math.hypot(x - vx, y - vy) < R + vr for vx, vy, vr in via):
            return False
        if any(rect_d((x, y), r) < R for r in rects):
            return False
        return not any(abs(a[0] - x) < 40 and seg_d((x, y), a, e) < R + hw for a, e, hw in trk)
    xs = [p[0] for p in POLY]
    ys = [p[1] for p in POLY]
    corners = [(min(xs) + 4, min(ys) + 4), (max(xs) - 4, min(ys) + 4), (min(xs) + 4, max(ys) - 4)]
    for n, (cx, cy) in enumerate(corners):
        best = None
        for r in range(0, 400):
            ring = r * 0.5
            for k in range(max(1, int(ring * 6))):
                a = 2 * math.pi * k / max(1, int(ring * 6))
                x, y = round(cx + ring * math.cos(a), 1), round(cy + ring * math.sin(a), 1)
                if free(x, y) and all(math.hypot(x - q[0], y - q[1]) > 25 for q in done if q[2] == side):
                    best = (x, y)
                    break
            if best:
                break
        if not best:
            print('no room for a fiducial near %.0f, %.0f on %s' % (cx, cy, side))
            continue
        fp = pcbnew.FootprintLoad(os.path.join(M.FPDIR, 'Fiducial.pretty'), 'Fiducial_1mm_Mask2mm')
        fp.SetReference('FID%d' % (len(done) + 1))
        fp.Reference().SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(F(best[0]), F(best[1])))
        if side == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM) if hasattr(pcbnew, 'FLIP_DIRECTION_TOP_BOTTOM') else fp.Flip(fp.GetPosition(), False)
        done.append((best[0], best[1], side))
        print('FID%d on %s at %.1f, %.1f (%.1f mm from the corner target)' % (len(done), side, best[0], best[1], math.hypot(best[0] - cx, best[1] - cy)))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
