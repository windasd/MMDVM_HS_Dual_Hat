"""Wide VBUS from the USB-C connector to the charger (run with KiCad python, after power_layout.py).

The autorouted VBUS ran 50 mm on In2 (0.4 mm, half-ounce copper) and cut the reference strip of the USB pair.
New path: B.Cu 1.0 .. 2.0 mm, over the USB pair on F.Cu (via arrays each side), B.Cu down to the charger.
C102 (1 uF) moves from the connector to the charger VBUS pin; C80 moves 1.5 mm to free the crossing.

  python vbus_path.py check    report anything closer than 0.2 mm to the planned copper (nothing is changed)
  python vbus_path.py place    move C102 and C80
  python vbus_path.py rip      remove the old VBUS and the tracks in the way (BTN_INT_N on B.Cu: re-route it)
  python vbus_path.py copper   draw the new copper (locked), refill the zones

Coordinates are board mm as shown in the PCB editor.
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
mm, F = pcbnew.ToMM, pcbnew.FromMM
FCU, I2, BCU = pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu
CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
PLACE = {'C102': (161.6, 146.3, 'W'), 'C80': (149.32, 115.75, 'S')}     # pad 1 on the west / south side
XW, XE, YB = (145.6, 146.45), (151.7, 152.55), 113.78                    # via columns of the bridge, its y
COL = 160.15                                                             # B.Cu run down to the charger
# (net, layer, width, points)
TRACKS = [
    ('VBUS', BCU, 1.0, [(124.6, 95.12), (125.69, 95.25)]),
    ('VBUS', BCU, 1.0, [(128.82, 100.05), (129.3, 101.1), (134.5, 106.3), (135.1, 106.3)]),
    ('VBUS', FCU, 0.6, [(134.2, 106.45), (135.4, 106.3)]),
    ('VBUS', FCU, 1.5, [(135.4, 106.3), (135.5, 107.0), (135.5, 109.9), (137.2, 109.9), (137.2, 111.9)]),
    ('VBUS', BCU, 2.0, [(137.3, 111.95), (139.13, YB), (XW[1], YB)]),
    ('VBUS', FCU, 1.4, [(XW[0], YB), (XE[1], YB)]),
    ('VBUS', BCU, 1.8, [(XE[0], YB), (157.0, YB), (COL, 116.93), (COL, 144.35)]),
    ('VBUS', FCU, 1.5, [(COL, 143.9), (COL, 144.8), (160.8, 146.3)]),
    ('VBUS', FCU, 0.7, [(160.8, 146.3), (160.66, 147.59)]),
    ('VBUS', FCU, 0.4, [(165.21, 143.04), (161.4, 143.04), (160.55, 143.9)]),
    ('GND', FCU, 0.4, [(162.375, 146.3), (163.3, 146.3)]),
    ('GND', FCU, 0.2, [(148.25, 114.92), (148.6, 115.27), (149.32, 115.27)]),
    ('+3V3_MESH', I2, 0.2, [(150.82, 114.45), (150.82, 115.75)]),
    ('+3V3_MESH', FCU, 0.2, [(150.82, 115.75), (150.34, 116.23), (149.32, 116.23), (149.32, 124.65)]),
]
# (net, x, y, diameter, drill)
VIAS = [('VBUS', 124.6, 95.12, 0.6, 0.3), ('VBUS', 134.2, 106.45, 0.6, 0.3)] + \
       [('VBUS', x, y, 0.6, 0.3) for x, y in ((136.75, 111.5), (137.55, 111.5), (136.75, 112.3))] + \
       [('VBUS', x, y, 0.6, 0.3) for x in XW + XE for y in (YB - 0.48, YB + 0.48)] + \
       [('VBUS', x, y, 0.6, 0.3) for x in (COL - 0.4, COL + 0.4) for y in (143.9, 144.8)] + \
       [('GND', 163.3, 146.3, 0.45, 0.2), ('+3V3_MESH', 150.82, 115.75, 0.5, 0.3)]
# old copper that goes: (net, layer or None for a via, end points)
OLD = [
    ('VBUS', BCU, (135.40, 106.30, 135.07, 106.30)), ('VBUS', BCU, (135.07, 106.30, 128.82, 100.05)),
    ('VBUS', None, (160.79, 134.60)),
    ('VBUS', FCU, (160.79, 134.60, 160.79, 138.61)), ('VBUS', FCU, (160.79, 138.61, 165.21, 143.04)),
    ('VBUS', FCU, (160.66, 147.59, 165.21, 143.04)), ('VBUS', FCU, (139.50, 108.26, 139.50, 105.04)),
    ('VBUS', FCU, (137.86, 109.90, 139.50, 108.26)), ('VBUS', FCU, (139.49, 105.05, 137.25, 105.05)),
    ('VBUS', FCU, (139.50, 105.04, 139.49, 105.05)),
    ('GND', FCU, (148.25, 114.92, 148.25, 114.84)), ('GND', FCU, (148.25, 114.84, 149.32, 113.77)),
    ('+3V3_MESH', FCU, (149.32, 114.73, 149.60, 114.45)), ('+3V3_MESH', FCU, (149.60, 114.45, 150.82, 114.45)),
    ('+3V3_MESH', FCU, (149.32, 124.65, 149.32, 114.73)), ('+3V3_MESH', None, (150.82, 114.45)),
    ('+3V3_MESH', I2, (150.82, 114.45, 151.04, 114.68)),
    ('BTN_INT_N', BCU, (164.99, 113.13, 165.48, 113.13)), ('BTN_INT_N', BCU, (164.99, 113.13, 155.87, 122.25)),
    ('BTN_INT_N', BCU, (155.87, 122.25, 155.87, 149.27)),
]
ZERO = [(149.32, 113.77), (149.32, 114.73), (139.50, 105.04)]       # zero-length leftovers on the moved pads


def near(a, b, tol=0.015):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def doomed(t):
    net = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        p = (mm(t.GetPosition().x), mm(t.GetPosition().y))
        return any(n == net and ly is None and near(p, q) for n, ly, q in OLD)
    a, e = (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))
    if net == 'VBUS' and t.GetLayer() == I2:
        return True
    if near(a, e) and any(near(a, z) for z in ZERO):
        return True
    for n, ly, q in OLD:
        if n == net and ly == t.GetLayer() and ((near(a, q[:2]) and near(e, q[2:])) or (near(a, q[2:]) and near(e, q[:2]))):
            return True
    return False


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0.0, p[0] - r[2]), max(r[1] - p[1], 0.0, p[1] - r[3]))


def check(board, need=0.2):
    """Gap between the planned copper and everything of another net that stays."""
    moved = {r: v for r, v in PLACE.items()}
    obst = []          # (kind, layers, geometry, net, label)
    for t in board.GetTracks():
        if doomed(t):
            continue
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            obst.append(('c', CU, (mm(p.x), mm(p.y), mm(t.GetWidth(FCU)) / 2), t.GetNetname(), 'via'))
        else:
            a, e = t.GetStart(), t.GetEnd()
            obst.append(('s', (t.GetLayer(),), ((mm(a.x), mm(a.y)), (mm(e.x), mm(e.y)), mm(t.GetWidth()) / 2),
                         t.GetNetname(), 'track'))
    for fp in board.GetFootprints():
        if fp.GetReference() in moved:
            continue                             # checked by the DRC after the move
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            obst.append(('r', tuple(ly for ly in CU if p.IsOnLayer(ly)) or CU, r, p.GetNetname(),
                         fp.GetReference() + '.' + p.GetNumber()))
    new = []           # (net, layers, point, radius, label)
    for net, ly, w, pts in TRACKS:
        for a, e in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(e[0] - a[0], e[1] - a[1]) / 0.05))
            for k in range(n + 1):
                new.append((net, (ly,), (a[0] + (e[0] - a[0]) * k / n, a[1] + (e[1] - a[1]) * k / n), w / 2,
                            '%s %s %.1f' % (net, board.GetLayerName(ly), w)))
    for net, x, y, d, _ in VIAS:
        new.append((net, CU, (x, y), d / 2, '%s via' % net))
    worst = {}
    for net, lys, p, r, lab in new:
        for kind, olys, g, onet, olab in obst:
            if onet == net or not set(lys) & set(olys):
                continue
            if kind == 'c':
                d = math.hypot(p[0] - g[0], p[1] - g[1]) - g[2]
            elif kind == 's':
                if abs(p[0] - g[0][0]) > 40 and abs(p[0] - g[1][0]) > 40:
                    continue
                d = seg_d(p, g[0], g[1]) - g[2]
            else:
                d = rect_d(p, g)
            d -= r
            if d < need:
                key = (lab, olab, onet, round(g[0] if kind != 's' else g[0][0], 1), round(g[1] if kind != 's' else g[0][1], 1))
                if key not in worst or d < worst[key][0]:
                    worst[key] = (d, p)
    for key, (d, p) in sorted(worst.items(), key=lambda kv: kv[1][0]):
        print('%6.2f mm  %-22s at %.2f, %.2f  <->  %s %s (%.1f, %.1f)' % (d, key[0], p[0], p[1], key[1], key[2], key[3], key[4]))
    print('conflicts below %.2f mm: %d' % (need, len(worst)))
    return len(worst)


def place():
    board = pcbnew.LoadBoard(PCB)
    for ref, (x, y, side) in PLACE.items():
        fp = [f for f in board.GetFootprints() if f.GetReference() == ref][0]
        for rot in (0, 90, 180, 270):
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
            p = {q.GetNumber(): q.GetPosition() for q in fp.Pads()}
            if (side == 'W' and p['1'].x < p['2'].x - F(0.5)) or (side == 'S' and p['1'].y > p['2'].y + F(0.5)):
                break
        print(ref, ' '.join('%s@%.3f,%.3f' % (q.GetNumber(), mm(q.GetPosition().x), mm(q.GetPosition().y)) for q in fp.Pads()))
    board.Save(PCB)


def rip():
    board = pcbnew.LoadBoard(PCB)
    kill = [t for t in board.GetTracks() if doomed(t)]
    for t in kill:
        board.Remove(t)
    print('removed', len(kill))
    board.Save(PCB)


def copper():
    board = pcbnew.LoadBoard(PCB)
    if check(board, 0.1):
        print('NOT DRAWN: clear the conflicts first')
        return
    for net, ly, w, pts in TRACKS:
        for a, e in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
            t.SetWidth(F(w))
            t.SetLayer(ly)
            t.SetNet(board.FindNet(net))
            t.SetLocked(net == 'VBUS')
            board.Add(t)
    for net, x, y, d, drill in VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
        v.SetWidth(pcbnew.F_Cu, F(d))
        v.SetDrill(F(drill))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(board.FindNet(net))
        v.SetLocked(net == 'VBUS')
        board.Add(v)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print('VBUS copper drawn: %d segments, %d vias' % (sum(len(t[3]) - 1 for t in TRACKS), len(VIAS)))


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(pcbnew.LoadBoard(PCB))
    else:
        {'place': place, 'rip': rip, 'copper': copper}[sys.argv[1]]()
    sys.stdout.flush()
    os._exit(0)
