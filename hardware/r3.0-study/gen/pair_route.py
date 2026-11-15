"""Lay the differential pairs before autorouting (run with KiCad's python, right after main_pcb.py).

Each pair is routed as one "fat" path on a single layer (A* on a 0.1 mm grid with a turn penalty) and then
split into two parallel tracks. The tracks are locked, so the autorouter keeps them and only completes the
short ends at the pins and the terminations.

Geometry for JLCPCB JLC04161H-7628 (1.6 mm, 4 layers; outer copper 35 um over 0.2104 mm prepreg, Er 4.4),
edge-coupled microstrip, IPC-2141 approximation -- to be confirmed with the fab's impedance calculator:
    100 ohm (Ethernet): W 0.20 / S 0.14 mm      90 ohm (USB): W 0.25 / S 0.14 mm
F.Cu is referenced to the In1 ground plane. The USB pair runs on B.Cu, whose neighbour In2 is a signal
layer, so a ground strip is reserved on In2 under it (rule area now, filled by usb_ref_plane.py later).

Usage: python pair_route.py
"""
import heapq
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
G = 0.1
CL = 0.15                     # copper clearance kept around the pair envelope
MARGIN = 14.0
EXTRA = 0.05                  # added spacing to other tracks (pairs, locked r1.3 copper)
POLY = [(M.X0 + x, M.Y0 - y) for x, y in M.OUTLINE]
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
fps = {f.GetReference(): f for f in board.GetFootprints()}


def pad(ref, num):
    return [p for p in fps[ref].Pads() if p.GetNumber() == num][0]


def in_board(x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / float(y2 - y1):
            c = not c
    return c


def edge_dist(x, y):
    d = 1e9
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        d = min(d, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return d


def route_pair(name, a, b, layer, w, s, exit_a=None, goal_r=2.5):
    """a, b: ((ref, pin_p), (ref, pin_n)). Returns the centre polyline (board mm) or None."""
    pa = [pad(*x) for x in a]
    pb = [pad(*x) for x in b]
    nets = [p.GetNetname() for p in pa]
    assert nets == [p.GetNetname() for p in pb], (nets, [p.GetNetname() for p in pb])
    pitch = w + s
    hw = pitch / 2 + w / 2                       # envelope half width
    R = hw + CL
    mid = lambda ps: ((tomm(ps[0].GetPosition().x) + tomm(ps[1].GetPosition().x)) / 2,
                      (tomm(ps[0].GetPosition().y) + tomm(ps[1].GetPosition().y)) / 2)
    (ax, ay), (bx, by) = mid(pa), mid(pb)
    x0, y0 = min(ax, bx) - MARGIN, min(ay, by) - MARGIN
    nx, ny = int((max(ax, bx) + MARGIN - x0) / G) + 1, int((max(ay, by) + MARGIN - y0) / G) + 1
    occ = bytearray(nx * ny)

    def mark(cx0, cy0, cx1, cy1, test):
        i0, i1 = max(0, int((cx0 - x0) / G)), min(nx - 1, int((cx1 - x0) / G) + 1)
        j0, j1 = max(0, int((cy0 - y0) / G)), min(ny - 1, int((cy1 - y0) / G) + 1)
        for j in range(j0, j1 + 1):
            y = y0 + j * G
            for i in range(i0, i1 + 1):
                if test(x0 + i * G, y):
                    occ[j * nx + i] = 1

    own = {id(p) for p in pa + pb}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if id(p) in own or (p.GetNetname() in nets and p.GetNetname()):
                continue
            through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if not (through or p.IsOnLayer(layer)):
                continue
            bb = p.GetBoundingBox()
            r = (tomm(bb.GetX()) - R, tomm(bb.GetY()) - R, tomm(bb.GetRight()) + R, tomm(bb.GetBottom()) + R)
            mark(r[0], r[1], r[2], r[3], lambda x, y: True)
    for t in board.GetTracks():
        if t.GetNetname() in nets:
            continue
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition()
            cx, cy, rr = tomm(q.x), tomm(q.y), tomm(t.GetWidth(pcbnew.F_Cu)) / 2 + R
            mark(cx - rr, cy - rr, cx + rr, cy + rr, lambda x, y, cx=cx, cy=cy, rr=rr: (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr)
        elif t.GetLayer() == layer:
            s_, e_ = t.GetStart(), t.GetEnd()
            x1, y1, x2, y2 = tomm(s_.x), tomm(s_.y), tomm(e_.x), tomm(e_.y)
            rr = tomm(t.GetWidth()) / 2 + R + EXTRA       # extra room to other pairs and locked tracks
            dx, dy = x2 - x1, y2 - y1
            ll = dx * dx + dy * dy

            def test(x, y, x1=x1, y1=y1, dx=dx, dy=dy, ll=ll, rr=rr):
                t_ = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ll))
                return (x - x1 - t_ * dx) ** 2 + (y - y1 - t_ * dy) ** 2 <= rr * rr
            mark(min(x1, x2) - rr, min(y1, y2) - rr, max(x1, x2) + rr, max(y1, y2) + rr, test)
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * G, y0 + j * G
            if not in_board(x, y) or edge_dist(x, y) < 0.35 + hw:
                occ[j * nx + i] = 1
    si, sj = int(round((ax - x0) / G)), int(round((ay - y0) / G))
    ti, tj = int(round((bx - x0) / G)), int(round((by - y0) / G))
    # the first millimetre leaves the start pads along their axis (the envelope overlaps the pair's own pads)
    pre = []
    if exit_a:
        k = DIRS.index(exit_a)
        for n in range(1, 11):
            pre.append((si + exit_a[0] * n, sj + exit_a[1] * n))
        start = (pre[-1][0], pre[-1][1], k)
    else:
        start = (si, sj, -1)
    gr = int(goal_r / G)

    def ok(i, j):
        return 0 <= i < nx and 0 <= j < ny and not occ[j * nx + i]

    best = {start: 0.0}
    prev = {}
    heap = [(math.hypot(start[0] - ti, start[1] - tj), 0.0, start)]
    found = None
    while heap:
        f, g, cur = heapq.heappop(heap)
        i, j, d = cur
        if (i - ti) ** 2 + (j - tj) ** 2 <= gr * gr:
            found = cur
            break
        if g > best.get(cur, 1e18):
            continue
        for k, (di, dj) in enumerate(DIRS):
            if d >= 0:
                turn = min((k - d) % 8, (d - k) % 8)
                if turn > 2:
                    continue
            else:
                turn = 0
            ni, nj = i + di, j + dj
            if not ok(ni, nj) or (di and dj and not (ok(ni, j) and ok(i, nj))):
                continue
            c = (1.4142 if di and dj else 1.0) + (0.0, 3.0, 12.0)[turn]
            n = (ni, nj, k)
            ng = g + c
            if ng < best.get(n, 1e18):
                best[n] = ng
                prev[n] = cur
                heapq.heappush(heap, (ng + math.hypot(ni - ti, nj - tj), ng, n))
    if found is None:
        print('NO PATH for pair', name)
        return None
    cells = [found]
    while cells[-1] in prev:
        cells.append(prev[cells[-1]])
    cells.reverse()
    pts = [(si, sj)] + pre[:-1] + [(c[0], c[1]) for c in cells] if exit_a else [(c[0], c[1]) for c in cells]
    # vertices where the direction changes
    vs = [pts[0]]
    for n in range(1, len(pts) - 1):
        d1 = (pts[n][0] - pts[n - 1][0], pts[n][1] - pts[n - 1][1])
        d2 = (pts[n + 1][0] - pts[n][0], pts[n + 1][1] - pts[n][1])
        if d1 != d2:
            vs.append(pts[n])
    vs.append(pts[-1])
    line = [(x0 + i * G, y0 + j * G) for i, j in vs]
    line[0] = (ax, ay)

    def offset(side):
        out = []
        d = side * pitch / 2
        for n, (x, y) in enumerate(line):
            segs = []
            if n > 0:
                segs.append((line[n - 1], (x, y)))
            if n < len(line) - 1:
                segs.append(((x, y), line[n + 1]))
            ns = []
            for (p, q) in segs:
                ll = math.hypot(q[0] - p[0], q[1] - p[1])
                ns.append((-(q[1] - p[1]) / ll, (q[0] - p[0]) / ll))
            if len(ns) == 1:
                out.append((x + d * ns[0][0], y + d * ns[0][1]))
            else:
                bx_, by_ = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]
                bl = math.hypot(bx_, by_)
                k = d / (bl / 2) / bl * 1.0          # mitre: offset / cos(half angle), along the bisector
                out.append((x + bx_ * k, y + by_ * k))
        return out

    # which side is the P line: the one whose start is nearer to the P pad
    left, right = offset(+1), offset(-1)
    ppos = (tomm(pa[0].GetPosition().x), tomm(pa[0].GetPosition().y))
    if math.hypot(left[0][0] - ppos[0], left[0][1] - ppos[1]) > math.hypot(right[0][0] - ppos[0], right[0][1] - ppos[1]):
        left, right = right, left
    lens = []
    for poly, p_pad in ((left, pa[0]), (right, pa[1])):
        net = board.FindNet(p_pad.GetNetname())
        chain = [(tomm(p_pad.GetPosition().x), tomm(p_pad.GetPosition().y))] + poly
        length = 0.0
        for (p, q) in zip(chain, chain[1:]):
            if math.hypot(q[0] - p[0], q[1] - p[1]) < 0.01:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(mm(p[0]), mm(p[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(q[0]), mm(q[1])))
            t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net); t.SetLocked(True)
            board.Add(t)
            length += math.hypot(q[0] - p[0], q[1] - p[1])
        lens.append(length)
    print('%-8s %s  P %.2f mm  N %.2f mm  skew %.2f mm  %d corners' % (
        name, board.GetLayerName(layer), lens[0], lens[1], abs(lens[0] - lens[1]), len(line) - 2))
    return line


def strip_polygon(line, half):
    """Outline of a band of the given half width along the centre polyline."""
    def side(sgn):
        out = []
        for n, (x, y) in enumerate(line):
            ns = []
            if n > 0:
                p = line[n - 1]
                ll = math.hypot(x - p[0], y - p[1]); ns.append((-(y - p[1]) / ll, (x - p[0]) / ll))
            if n < len(line) - 1:
                q = line[n + 1]
                ll = math.hypot(q[0] - x, q[1] - y); ns.append((-(q[1] - y) / ll, (q[0] - x) / ll))
            bx_, by_ = sum(v[0] for v in ns), sum(v[1] for v in ns)
            bl = math.hypot(bx_, by_)
            k = sgn * half / (bl / len(ns)) / bl
            out.append((x + bx_ * k, y + by_ * k))
        return out
    return side(+1) + side(-1)[::-1]


ETH = [('TR0', '44', '43', '2', '3'), ('TR1', '47', '46', '4', '5'), ('TR2', '52', '51', '6', '7'),
       ('TR3', '55', '54', '8', '9')]
# U60 is placed with its TR pins facing the RJ45 (+x on the board)
for name, p, n, jp, jn in [ETH[k] for k in (3,2,1,0)]:
    route_pair(name, (('U60', p), ('U60', n)), (('J60', jp), ('J60', jn)), pcbnew.F_Cu, 0.20, 0.14, exit_a=(1, 0),
               goal_r=4.5)
usb = route_pair('USB', (('J10', '51'), ('J10', '53')), (('U60', '13'), ('U60', '12')), pcbnew.B_Cu, 0.25, 0.14,
                 goal_r=4.5)
if usb:
    # In2 under the USB pair: no other tracks (reference plane), ground vias beside the pair every ~6 mm
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetLayer(pcbnew.In2_Cu)
    z.SetZoneName('USB_REF')
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False)
    z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in strip_polygon(usb, 1.3):
        ol.Append(mm(x), mm(y))
    board.Add(z)
    gnd = board.FindNet('GND')
    pads_all = [p for fp in board.GetFootprints() for p in fp.Pads()]
    tracks = list(board.GetTracks())
    run = 3.0
    nv = 0
    for (p, q) in zip(usb, usb[1:]):
        ll = math.hypot(q[0] - p[0], q[1] - p[1])
        ux, uy = (q[0] - p[0]) / ll, (q[1] - p[1]) / ll
        while run < ll:
            for sgn in (1, -1):
                vx, vy = p[0] + ux * run - uy * 0.9 * sgn, p[1] + uy * run + ux * 0.9 * sgn
                pt = pcbnew.VECTOR2I(mm(vx), mm(vy))
                acc = mm(0.45 / 2 + 0.15)
                if not in_board(vx, vy) or edge_dist(vx, vy) < 0.8:
                    continue
                if any(o.GetNetname() != 'GND' and o.HitTest(pt, acc) for o in pads_all) or \
                        any(o.GetNetname() != 'GND' and o.HitTest(pt, acc) for o in tracks):
                    continue
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pt); v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(gnd); v.SetLocked(True)
                board.Add(v)
                nv += 1
            run += 6.0
        run -= ll
    print('USB reference strip on In2 (rule area), ground vias beside the pair:', nv)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
