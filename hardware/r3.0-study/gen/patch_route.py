"""Route single connections the autorouter gave up on (run with KiCad's python).

A plain grid maze router (A*, 0.1 mm grid, F.Cu / In2.Cu / B.Cu, through vias) between two pads of one net.
Everything of other nets is an obstacle with the board clearance; the new copper is 0.2 mm track and
0.45 / 0.2 mm vias. Zones are refilled afterwards. No length matching or impedance control: use it to close
connections, then review them.

Usage: python patch_route.py U60.12 J10.51 [REF.PAD REF.PAD ...]
`REF.PAD VIA` (ground pads): run to the nearest spot where a via fits and drop a via to the ground plane.
An end can also be a point on an existing track of the net: @x,y,LAYER (board mm, e.g. @148.76,94.33,F.Cu).
"""
import heapq
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
G = 0.1                       # grid, mm
W, VIA_D, VIA_DR, CL = 0.2, 0.45, 0.2, 0.1
R_TRK = W / 2 + CL + 0.03     # obstacle inflation for a track centre line
R_VIA = VIA_D / 2 + CL + 0.01    # exact distance test from the via centre, so a small margin is enough
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
MARGIN = float(os.environ.get('PR_MARGIN', '9.0'))
VIA_COST = 40.0
tomm = pcbnew.ToMM
POLY = [(M.X0 + x, M.Y0 - y) for x, y in M.OUTLINE]


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


class Point:
    """A spot on existing copper, given as @x,y,LAYER (board mm): stands in for a pad at either end."""

    def __init__(self, spec):
        x, y, layer = spec[1:].split(',')
        self.q = pcbnew.VECTOR2I(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))
        if layer == 'ANY':                       # whatever copper ends there (a track end or a via)
            hit = [t for t in board.GetTracks() if t.HitTest(self.q, pcbnew.FromMM(0.05))]
            trk = [t for t in hit if t.GetClass() == 'PCB_TRACK']
            self.layer = trk[0].GetLayer() if trk else pcbnew.F_Cu
            self.any = bool([t for t in hit if t.GetClass() == 'PCB_VIA'])
        else:
            self.layer = board.GetLayerID(layer)
            self.any = False
            hit = [t for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == self.layer
                   and t.HitTest(self.q, pcbnew.FromMM(0.05))]
        if not hit:
            raise SystemExit('no track at ' + spec)
        self.net = hit[0].GetNetname()

    def GetNetname(self):
        return self.net

    def GetPosition(self):
        return self.q

    def GetBoundingBox(self):
        return pcbnew.BOX2I(self.q - pcbnew.VECTOR2I(pcbnew.FromMM(0.05), pcbnew.FromMM(0.05)),
                            pcbnew.VECTOR2I(pcbnew.FromMM(0.1), pcbnew.FromMM(0.1)))

    def GetAttribute(self):
        return pcbnew.PAD_ATTRIB_SMD

    def IsOnLayer(self, layer):
        return self.any or layer == self.layer


def find_pad(spec):
    if spec.startswith('@'):
        return Point(spec)
    ref, num = spec.split('.')
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetNumber() == num:
                    return p
    raise SystemExit('no pad ' + spec)


def route(spec_a, spec_b):
    pa = find_pad(spec_a)
    to_via = spec_b == 'VIA'          # GND only: run to the nearest spot where a via fits and drop one there
    pb = pa if to_via else find_pad(spec_b)
    net = pa.GetNetname()
    assert net == pb.GetNetname(), (net, pb.GetNetname())
    ax, ay = tomm(pa.GetPosition().x), tomm(pa.GetPosition().y)
    bx, by = tomm(pb.GetPosition().x), tomm(pb.GetPosition().y)
    x0, y0 = min(ax, bx) - MARGIN, min(ay, by) - MARGIN
    # put the start exactly on a grid node, so no tiny snap segment is needed there
    x0 = ax - math.ceil((ax - x0) / G) * G
    y0 = ay - math.ceil((ay - y0) / G) * G
    nx = int((max(ax, bx) + MARGIN - x0) / G) + 1
    ny = int((max(ay, by) + MARGIN - y0) / G) + 1
    occ = [bytearray(nx * ny) for _ in LAYERS]       # blocked for a track centre
    vocc = bytearray(nx * ny)                        # blocked for a via centre

    def mark(grid, cx0, cy0, cx1, cy1, test):
        i0, i1 = max(0, int((cx0 - x0) / G)), min(nx - 1, int((cx1 - x0) / G) + 1)
        j0, j1 = max(0, int((cy0 - y0) / G)), min(ny - 1, int((cy1 - y0) / G) + 1)
        for j in range(j0, j1 + 1):
            y = y0 + j * G
            row = j * nx
            for i in range(i0, i1 + 1):
                if test(x0 + i * G, y):
                    grid[row + i] = 1

    def add_obstacle(layers, shape, r_extra):
        """shape = ('seg', x1, y1, x2, y2, half) | ('rect', x1, y1, x2, y2) | ('circ', x, y, r)"""
        for infl, grids in ((R_TRK, [occ[k] for k in layers]), (R_VIA, [vocc])):
            if shape[0] == 'seg':
                _, x1, y1, x2, y2, half = shape
                rr = half + infl
                dx, dy = x2 - x1, y2 - y1
                ll = dx * dx + dy * dy

                def test(x, y, x1=x1, y1=y1, dx=dx, dy=dy, ll=ll, rr=rr):
                    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ll))
                    return (x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2 <= rr * rr
                bb = (min(x1, x2) - rr, min(y1, y2) - rr, max(x1, x2) + rr, max(y1, y2) + rr)
            elif shape[0] == 'rect':
                _, x1, y1, x2, y2 = shape
                bb = (x1 - infl, y1 - infl, x2 + infl, y2 + infl)

                def test(x, y, bb=bb):
                    return bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]
            else:
                _, cx, cy, r = shape
                rr = r + infl

                def test(x, y, cx=cx, cy=cy, rr=rr):
                    return (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr
                bb = (cx - rr, cy - rr, cx + rr, cy + rr)
            if bb[2] < x0 or bb[0] > x0 + nx * G or bb[3] < y0 or bb[1] > y0 + ny * G:
                return
            for g in grids:
                mark(g, bb[0], bb[1], bb[2], bb[3], test)

    allk = [0, 1, 2]
    for t in board.GetTracks():
        if t.GetNetname() == net:
            if t.GetClass() == 'PCB_VIA':            # no second via within hole-to-hole distance
                q = t.GetPosition()
                mark(vocc, tomm(q.x) - 0.5, tomm(q.y) - 0.5, tomm(q.x) + 0.5, tomm(q.y) + 0.5,
                     lambda x, y, cx=tomm(q.x), cy=tomm(q.y): 0.01 < math.hypot(x - cx, y - cy) < 0.5)
            continue
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition()
            add_obstacle(allk, ('circ', tomm(q.x), tomm(q.y), tomm(t.GetWidth(pcbnew.F_Cu)) / 2), 0)
        elif t.GetLayer() in LAYERS:
            s, e = t.GetStart(), t.GetEnd()
            add_obstacle([LAYERS.index(t.GetLayer())],
                         ('seg', tomm(s.x), tomm(s.y), tomm(e.x), tomm(e.y), tomm(t.GetWidth()) / 2), 0)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.GetNetname():
                continue
            b = p.GetBoundingBox()
            through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            ks = allk if through else [k for k, ly in enumerate(LAYERS) if p.IsOnLayer(ly)]
            shape = ('rect', tomm(b.GetX()), tomm(b.GetY()), tomm(b.GetRight()), tomm(b.GetBottom()))
            if ks:
                add_obstacle(ks, shape, 0)
            else:                                   # inner layers are free, but no via may land on the pad
                mark(vocc, shape[1] - R_VIA, shape[2] - R_VIA, shape[3] + R_VIA, shape[4] + R_VIA, lambda x, y: True)
    # rule areas that forbid tracks (the reserved reference strip under the USB pair on In2)
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.GetLayer() in LAYERS:
            g = occ[LAYERS.index(z.GetLayer())]
            ol = z.Outline()
            bb = z.GetBoundingBox()
            i0, i1 = max(0, int((tomm(bb.GetX()) - x0) / G)), min(nx - 1, int((tomm(bb.GetRight()) - x0) / G) + 1)
            j0, j1 = max(0, int((tomm(bb.GetY()) - y0) / G)), min(ny - 1, int((tomm(bb.GetBottom()) - y0) / G) + 1)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    if ol.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x0 + i * G), pcbnew.FromMM(y0 + j * G)), -1,
                                   pcbnew.FromMM(W / 2 + 0.05)):
                        g[j * nx + i] = 1
    # board edge
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * G, y0 + j * G
            if not in_board(x, y) or edge_dist(x, y) < 0.3 + W / 2 + 0.05:
                for g in occ:
                    g[j * nx + i] = 1
                vocc[j * nx + i] = 1
            elif edge_dist(x, y) < 0.3 + VIA_D / 2 + 0.05:
                vocc[j * nx + i] = 1

    def cell(x, y):
        return int(round((x - x0) / G)), int(round((y - y0) / G))

    def pad_layers(p):
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            return allk
        return [k for k, ly in enumerate(LAYERS) if p.IsOnLayer(ly)]

    si, sj = cell(ax, ay)
    ti, tj = cell(bx, by)
    tb = pb.GetBoundingBox()
    goal = set()
    for k in pad_layers(pb):
        for j in range(int((tomm(tb.GetY()) - y0) / G) + 1, int((tomm(tb.GetBottom()) - y0) / G) + 1):
            for i in range(int((tomm(tb.GetX()) - x0) / G) + 1, int((tomm(tb.GetRight()) - x0) / G) + 1):
                goal.add((k, i, j))
    goal.add((pad_layers(pb)[0], ti, tj))
    if to_via:
        goal = set()
    # the pads' own cells are always usable (clearance to neighbours is handled by leaving along the pad axis)
    sb = pa.GetBoundingBox()
    free_cells = set(goal)
    for k in pad_layers(pa):
        for j in range(int((tomm(sb.GetY()) - y0) / G) + 1, int((tomm(sb.GetBottom()) - y0) / G) + 1):
            for i in range(int((tomm(sb.GetX()) - x0) / G) + 1, int((tomm(sb.GetRight()) - x0) / G) + 1):
                free_cells.add((k, i, j))
    start = [(k, si, sj) for k in pad_layers(pa)]
    for s in start:
        free_cells.add(s)

    def ok(k, i, j):
        return 0 <= i < nx and 0 <= j < ny and ((k, i, j) in free_cells or not occ[k][j * nx + i])

    best, prev, heap = {}, {}, []
    for s in start:
        best[s] = 0.0
        heapq.heappush(heap, (math.hypot(s[1] - ti, s[2] - tj), 0.0, s))
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142),
             (-1, -1, 1.4142)]
    found = None
    while heap:
        f, g, cur = heapq.heappop(heap)
        if cur in goal or (to_via and not vocc[cur[2] * nx + cur[1]]):     # may end up as a via in the pad
            found = cur
            break
        if g > best.get(cur, 1e18):
            continue
        k, i, j = cur
        for di, dj, c in moves:
            ni, nj = i + di, j + dj
            if not ok(k, ni, nj):
                continue
            if di and dj and not (ok(k, ni, j) and ok(k, i, nj)):
                continue
            n = (k, ni, nj)
            ng = g + c
            if ng < best.get(n, 1e18):
                best[n] = ng
                prev[n] = cur
                heapq.heappush(heap, (ng + math.hypot(ni - ti, nj - tj), ng, n))
        if not vocc[j * nx + i]:
            for k2 in allk:
                if k2 != k and ok(k2, i, j):
                    n = (k2, i, j)
                    ng = g + VIA_COST
                    if ng < best.get(n, 1e18):
                        best[n] = ng
                        prev[n] = cur
                        heapq.heappush(heap, (ng + math.hypot(i - ti, j - tj), ng, n))
    if found is None:
        print('NO PATH', spec_a, spec_b, net)
        return False
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    ni = board.FindNet(net)
    pt = lambda i, j: pcbnew.VECTOR2I(pcbnew.FromMM(x0 + i * G), pcbnew.FromMM(y0 + j * G))
    # exact pad centres at both ends
    pts = [(c[0], pt(c[1], c[2])) for c in path]
    pts[0] = (pts[0][0], pa.GetPosition())
    segs = vias = 0
    i = 0
    while i < len(path) - 1:
        if path[i + 1][0] != path[i][0]:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pts[i][1]); v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DR)); v.SetNet(ni)
            board.Add(v)
            vias += 1
            i += 1
            continue
        d = (path[i + 1][1] - path[i][1], path[i + 1][2] - path[i][2])
        j = i + 1
        while j < len(path) - 1 and path[j + 1][0] == path[j][0] and                 (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == d:
            j += 1
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pts[i][1]); t.SetEnd(pts[j][1]); t.SetWidth(pcbnew.FromMM(W))
        t.SetLayer(LAYERS[path[i][0]]); t.SetNet(ni)
        board.Add(t)
        segs += 1
        i = j
    if to_via:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pts[-1][1]); v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DR)); v.SetNet(ni)
        board.Add(v)
        vias += 1
    # last cell to the target pad centre if the path stopped at the pad rim
    last = pts[-1][1]
    if not to_via and last != pb.GetPosition() and LAYERS[path[-1][0]] in [ly for ly in LAYERS if pb.IsOnLayer(ly)]:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(last); t.SetEnd(pb.GetPosition()); t.SetWidth(pcbnew.FromMM(W)); t.SetLayer(LAYERS[path[-1][0]])
        t.SetNet(ni)
        board.Add(t)
        segs += 1
    print('routed %s -> %s  %s: %.1f mm, %d segments, %d vias' % (spec_a, spec_b, net, best[found] * G, segs, vias))
    return True


args = sys.argv[1:]
done = [route(a, b) for a, b in zip(args[0::2], args[1::2])]
if any(done):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
sys.stdout.flush()
os._exit(0)
