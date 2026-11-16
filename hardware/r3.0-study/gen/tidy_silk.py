"""Tidy the silkscreen after placement (run with KiCad's python).

1. Footprint silk graphics that run over a pad of another footprint or over the board edge are removed
   (the fab would clip them anyway).
2. Every visible reference designator on silk is set to 0.8 mm text and moved to the first free spot next to
   its part: clear of pads, other silk, other references, holes and the board edge. Where no spot is free
   the reference is hidden on silk (it stays on the Fab layer for the assembly drawing).

Usage: python tidy_silk.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
TXT_H, TXT_T = 0.8, 0.12
PAD_CL = mm(0.15)       # silk to pad (mask opening) / hole
SILK_CL = mm(0.12)      # silk to silk
EDGE_CL = mm(0.45)
CELL = mm(2.0)
SILK = (pcbnew.F_SilkS, pcbnew.B_SilkS)

POLY = [(mm(M.X0 + x), mm(M.Y0 - y)) for x, y in M.OUTLINE]


def in_board(x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / float(y2 - y1):
            c = not c
    return c


def inside(x0, y0, x1, y1, margin=EDGE_CL):
    return all(in_board(x, y) for x in (x0 - margin, x1 + margin) for y in (y0 - margin, y1 + margin))


def box(item):
    b = item.GetBoundingBox()
    return (b.GetX(), b.GetY(), b.GetX() + b.GetWidth(), b.GetY() + b.GetHeight())


class Grid:
    def __init__(self):
        self.cells = {}

    def add(self, bx, tag):
        for i in range(int(bx[0] // CELL), int(bx[2] // CELL) + 1):
            for j in range(int(bx[1] // CELL), int(bx[3] // CELL) + 1):
                self.cells.setdefault((i, j), []).append((bx, tag))

    def hits(self, bx, cl, skip=None):
        for i in range(int((bx[0] - cl) // CELL), int((bx[2] + cl) // CELL) + 1):
            for j in range(int((bx[1] - cl) // CELL), int((bx[3] + cl) // CELL) + 1):
                for o, tag in self.cells.get((i, j), ()):
                    if tag != skip and o[0] < bx[2] + cl and o[2] > bx[0] - cl and o[1] < bx[3] + cl and o[3] > bx[1] - cl:
                        return True
        return False


fps = list(board.GetFootprints())
side = lambda fp: 0 if fp.GetLayer() == pcbnew.F_Cu else 1
pad_grid = [Grid(), Grid()]      # per side: pads with a mask opening there, and all drilled holes
pads_side = [[], []]
for fp in fps:
    for p in fp.Pads():
        through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        for s, cu in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
            if through or p.IsOnLayer(cu):
                pad_grid[s].add(box(p), fp.GetReference())
                pads_side[s].append((p, fp.GetReference(), box(p)))

# ---- 1. silk graphics over foreign pads or over the board edge
removed = 0
silk_grid = [Grid(), Grid()]
graphics = {fp.GetReference(): list(fp.GraphicalItems()) for fp in fps}     # read everything before removing
doomed = []
for fp in fps:
    for g in graphics[fp.GetReference()]:
        if g.GetLayer() not in SILK or g.GetClass() != 'PCB_SHAPE':
            continue
        s = 0 if g.GetLayer() == pcbnew.F_SilkS else 1
        bx = box(g)
        bad = not inside(*bx, margin=mm(0.2))
        if not bad and pad_grid[s].hits(bx, PAD_CL, skip=fp.GetReference()):
            if g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                a, e = g.GetStart(), g.GetEnd()
                n = max(1, int(max(abs(a.x - e.x), abs(a.y - e.y)) / mm(0.05)))
                reach = g.GetWidth() // 2 + PAD_CL
                for p, ref, pb in pads_side[s]:
                    if ref == fp.GetReference() or pb[0] > bx[2] + reach or pb[2] < bx[0] - reach \
                            or pb[1] > bx[3] + reach or pb[3] < bx[1] - reach:
                        continue
                    if any(p.HitTest(pcbnew.VECTOR2I(int(a.x + (e.x - a.x) * k / n), int(a.y + (e.y - a.y) * k / n)), reach)
                           for k in range(n + 1)):
                        bad = True
                        break
            else:
                # polygons / rectangles (pin-1 markers, outlines): only when the shape itself covers a pad
                bad = pad_grid[s].hits(bx, 0, skip=fp.GetReference())
        if bad:
            doomed.append((fp, g))
            removed += 1
        else:
            silk_grid[s].add(bx, fp.GetReference())
# board-level silk text / graphics are obstacles too
for d in board.GetDrawings():
    if d.GetLayer() in SILK:
        silk_grid[0 if d.GetLayer() == pcbnew.F_SilkS else 1].add(box(d), '#board')
# other visible silk texts of footprints (values, user text)
for fp in fps:
    for f in list(fp.GetFields()) + [g for g in graphics[fp.GetReference()] if g.GetClass() == 'PCB_TEXT']:
        if f.GetLayer() in SILK and f.IsVisible() and not (f.GetClass() == 'PCB_FIELD' and f.IsReference()):
            silk_grid[0 if f.GetLayer() == pcbnew.F_SilkS else 1].add(box(f), '#text')


# ---- 2. reference designators
def body(fp):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for it in list(fp.Pads()) + [g for g in graphics[fp.GetReference()] if g.GetClass() == 'PCB_SHAPE'
                                 and g.GetLayer() in SILK + (pcbnew.F_CrtYd, pcbnew.B_CrtYd)]:
        b = box(it)
        xs0.append(b[0]); ys0.append(b[1]); xs1.append(b[2]); ys1.append(b[3])
    return min(xs0), min(ys0), max(xs1), max(ys1)


def put(ref, cx, cy, ang):
    ref.SetTextAngleDegrees(ang)
    ref.SetPosition(pcbnew.VECTOR2I(int(cx), int(cy)))
    b = box(ref)
    ref.SetPosition(pcbnew.VECTOR2I(int(2 * cx - (b[0] + b[2]) / 2), int(2 * cy - (b[1] + b[3]) / 2)))
    return box(ref)


todo = []
for fp in fps:
    ref = fp.Reference()
    if ref.GetLayer() in SILK and ref.IsVisible():
        b = body(fp)
        todo.append(((b[2] - b[0]) * (b[3] - b[1]), fp, b))
todo.sort(key=lambda t: -t[0])
moved = hidden = 0
hidden_refs = []
for _, fp, b in todo:
    ref = fp.Reference()
    s = 0 if ref.GetLayer() == pcbnew.F_SilkS else 1
    ref.SetTextSize(pcbnew.VECTOR2I(mm(TXT_H), mm(TXT_H)))
    ref.SetTextThickness(mm(TXT_T))
    ref.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    ref.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t0 = put(ref, 0, 0, 0)
    w, h = t0[2] - t0[0], t0[3] - t0[1]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    cands = []
    for gap in (mm(0.2), mm(0.5), mm(0.9), mm(1.4)):
        for slide in (0, -0.5, 0.5, -1.0, 1.0):
            dx = slide * max(0, (b[2] - b[0]) / 2)
            dy = slide * max(0, (b[3] - b[1]) / 2)
            cands += [(cx + dx, b[1] - gap - h / 2, 0), (cx + dx, b[3] + gap + h / 2, 0),
                      (b[0] - gap - w / 2, cy + dy, 0), (b[2] + gap + w / 2, cy + dy, 0),
                      (b[0] - gap - h / 2, cy + dy, 90), (b[2] + gap + h / 2, cy + dy, 90)]
    ok = False
    for x, y, ang in cands:
        tb = put(ref, x, y, ang)
        if inside(*tb) and not pad_grid[s].hits(tb, PAD_CL) and not silk_grid[s].hits(tb, SILK_CL):
            silk_grid[s].add(tb, '#ref')
            moved += 1
            ok = True
            break
    if not ok:
        put(ref, cx, cy, 0)
        ref.SetVisible(False)
        hidden += 1
        hidden_refs.append(fp.GetReference())
for fp, g in doomed:
    fp.Remove(g)
board.Save(PCB)
print('silk graphics removed', removed, '| references placed', moved, '| hidden (no room)', hidden)
print('hidden:', ' '.join(sorted(hidden_refs)))
sys.stdout.flush()
os._exit(0)
