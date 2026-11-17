"""Ground vias at both sides of every cut in the USB reference strip (run with KiCad's python).

The USB pair runs on B.Cu (x 148.96 / 149.34, y 99 .. 204) over a ground strip on In2 (x 147.8 .. 150.4).
Tracks of other nets that cross the strip on In2 cut it. Where a crossing cannot be moved, the return current
of the pair has to step round the cut; the shortest way is a ground via right before and right after the cut,
which takes it down to the In1 plane and back. The strip already has ground vias every 6 mm in two columns
(x 148.25 west of the pair, x 150.05 east of it). This script adds, in each column and on each side of each
cut, a ground via within REACH of the cut where there is none yet, at the nearest spot that is clear of every
other net on all four layers.

Usage: python stitch_strip.py [--dry]
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
mm, F = pcbnew.ToMM, pcbnew.FromMM
SX0, SX1, SY0, SY1 = 147.8, 150.4, 99.0, 204.0
COLS = (148.25, 150.05)                 # the existing stitching columns
VIA_D, VIA_DR, CL, HOLE_GAP = 0.45, 0.2, 0.12, 0.25
REACH = 1.2                             # wanted: a ground via within this distance of the cut edge
SEARCH = 2.5                            # how far from the cut a new via may go
DRY = '--dry' in sys.argv
board = pcbnew.LoadBoard(PCB)


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0, p[0] - r[2]), max(r[1] - p[1], 0, p[1] - r[3]))


def xy(v):
    return (mm(v.x), mm(v.y))


tracks = [(t.GetNetname(), t.GetLayer(), xy(t.GetStart()), xy(t.GetEnd()), mm(t.GetWidth()) / 2)
          for t in board.GetTracks() if t.GetClass() != 'PCB_VIA']
vias = [(t.GetNetname(), xy(t.GetPosition()), mm(t.GetWidth(pcbnew.F_Cu)) / 2, mm(t.GetDrill()) / 2)
        for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
pads = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        b = p.GetBoundingBox()
        pads.append((p.GetNetname(), (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())),
                     p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH), mm(p.GetDrillSize().x) / 2))

# the cuts: In2 track segments of other nets inside the strip, as y ranges (with the zone clearance)
cuts = []
for net, ly, a, e, hw in tracks:
    if ly != pcbnew.In2_Cu or net == 'GND':
        continue
    if max(a[0], e[0]) < SX0 or min(a[0], e[0]) > SX1 or max(a[1], e[1]) < SY0 or min(a[1], e[1]) > SY1:
        continue
    # y extent of the track where it lies over the strip
    ys = []
    n = max(2, int(math.hypot(e[0] - a[0], e[1] - a[1]) / 0.05))
    for k in range(n + 1):
        x, y = a[0] + (e[0] - a[0]) * k / n, a[1] + (e[1] - a[1]) * k / n
        if SX0 - hw <= x <= SX1 + hw and SY0 <= y <= SY1:
            ys.append(y)
    if ys:
        cuts.append((min(ys) - hw - 0.2, max(ys) + hw + 0.2, net))
cuts.sort()
merged = []
for y0, y1, net in cuts:
    if merged and y0 <= merged[-1][1] + 0.3:
        merged[-1][1] = max(merged[-1][1], y1)
        merged[-1][2].add(net)
    else:
        merged.append([y0, y1, {net}])


def free(x, y):
    """A ground via at (x, y): clear of other nets on all layers, holes apart, inside the strip."""
    r = VIA_D / 2
    for net, ly, a, e, hw in tracks:
        if net == 'GND' or abs(a[1] - y) > 6 and abs(e[1] - y) > 6:
            continue
        if seg_d((x, y), a, e) < hw + r + CL:
            return False
    for net, c, vr, hr in vias:
        if abs(c[1] - y) > 3:
            continue
        d = math.hypot(c[0] - x, c[1] - y)
        if d < hr + VIA_DR / 2 + HOLE_GAP or (net != 'GND' and d < vr + r + CL):
            return False
    for net, rc, through, hr in pads:
        if rect_d((x, y), rc) > 3:
            continue
        if through and rect_d((x, y), rc) < r + 0.3:
            return False
        if net != 'GND' and rect_d((x, y), rc) < r + CL:
            return False
        if net == 'GND' and not through and rect_d((x, y), rc) < VIA_DR / 2 + 0.05:
            return False                     # not in an SMD pad either
    return SX0 + r <= x <= SX1 - r


added = []
for y0, y1, nets in merged:
    for side, edge in (('above', y0), ('below', y1)):
        for col in COLS:
            sign = -1 if side == 'above' else 1
            have = [c for net, c, vr, hr in vias + [('GND', a, 0, 0) for a in added]
                    if net == 'GND' and abs(c[0] - col) < 0.6 and 0 <= (c[1] - edge) * sign <= REACH]
            if have:
                continue
            spot = None
            for k in range(0, int(SEARCH / 0.05) + 1):
                y = round(edge + sign * (VIA_D / 2 + 0.05 + k * 0.05), 3)
                for dx in (0, -0.1, 0.1, -0.2, 0.2):
                    if free(col + dx, y):
                        spot = (round(col + dx, 3), y)
                        break
                if spot:
                    break
            if spot:
                added.append(spot)
                vias.append(('GND', spot, VIA_D / 2, VIA_DR / 2))
            print('cut y %.2f..%.2f %-40s %s, column %.2f: %s' % (
                y0, y1, ','.join(sorted(n.split('/')[-1] for n in nets))[:40], side, col,
                'via at %.2f, %.2f (%.2f mm from the cut)' % (spot[0], spot[1], abs(spot[1] - edge)) if spot else 'NO ROOM'))
print('cuts: %d, ground vias added: %d' % (len(merged), len(added)))
if not DRY and added:
    gnd = board.FindNet('GND')
    for x, y in added:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
        v.SetWidth(pcbnew.F_Cu, F(VIA_D))
        v.SetDrill(F(VIA_DR))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(gnd)
        v.SetLocked(True)
        board.Add(v)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
sys.stdout.flush()
os._exit(0)
