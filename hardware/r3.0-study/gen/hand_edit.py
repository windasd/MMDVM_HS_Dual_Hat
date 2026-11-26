"""Small hand edits on the routed board from a text file, with a clearance check (run with KiCad's python).

Lines of the edit file (board mm, '#' starts a comment):
  RM  <layer> x0,y0 x1,y1            remove the track between these end points
  RMVIA x,y                          remove the via there
  ROT <ref> <degrees>                turn a footprint about its centre (done in the rm run; check afterwards)
  MV  x0,y0 x1,y1                    move the via at the first point; track ends on it follow
  T   <net> <layer> <width> x,y x,y [x,y ...]      (a space in a net name is written %20)
  V   <net> x,y [diameter drill]     (default 0.45 / 0.2)

Usage: python hand_edit.py edits.txt check|rm|add
`check` reports copper of other nets closer than 0.1 mm to the new copper, ignoring what RM / RMVIA / MV take
away. `rm` and `add` are separate runs (pcbnew objects do not survive a removal in the same process).
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
mm, F = pcbnew.ToMM, pcbnew.FromMM
CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
board = pcbnew.LoadBoard(PCB)
RM, RMVIA, MV, T, V, ROT = [], [], [], [], [], []


def pt(s):
    x, y = s.split(',')
    return (float(x), float(y))


for line in open(sys.argv[1], encoding='utf-8'):
    f = line.split('#')[0].split()
    if not f:
        continue
    if f[0] == 'RM':
        RM.append((board.GetLayerID(f[1]), pt(f[2]), pt(f[3])))
    elif f[0] == 'RMVIA':
        RMVIA.append(pt(f[1]))
    elif f[0] == 'ROT':
        ROT.append((f[1], float(f[2])))
    elif f[0] == 'MV':
        MV.append((pt(f[1]), pt(f[2])))
    elif f[0] == 'T':
        T.append((f[1].replace('%20', ' '), board.GetLayerID(f[2]), float(f[3]), [pt(s) for s in f[4:]]))
    elif f[0] == 'V':
        V.append((f[1].replace('%20', ' '), pt(f[2]), float(f[3]) if len(f) > 3 else 0.45, float(f[4]) if len(f) > 4 else 0.2))
    else:
        raise SystemExit('bad line: ' + line)


def near(a, b, tol=0.02):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def xy(v):
    return (mm(v.x), mm(v.y))


def doomed(t):
    if t.GetClass() == 'PCB_VIA':
        return any(near(xy(t.GetPosition()), q) for q in RMVIA)
    a, e = xy(t.GetStart()), xy(t.GetEnd())
    return any(ly == t.GetLayer() and ((near(a, p) and near(e, q)) or (near(a, q) and near(e, p))) for ly, p, q in RM)


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0.0, p[0] - r[2]), max(r[1] - p[1], 0.0, p[1] - r[3]))


def moved(p):
    for a, e in MV:
        if near(p, a):
            return e
    return p


def check(need=0.1):
    obst, holes = [], []
    for t in board.GetTracks():
        if doomed(t):
            continue
        if t.GetClass() == 'PCB_VIA':
            c = moved(xy(t.GetPosition()))
            obst.append(('c', CU, (c[0], c[1], mm(t.GetWidth(pcbnew.F_Cu)) / 2), t.GetNetname(), 'via'))
            holes.append((c, mm(t.GetDrill()) / 2))
        else:
            obst.append(('s', (t.GetLayer(),), (moved(xy(t.GetStart())), moved(xy(t.GetEnd())), mm(t.GetWidth()) / 2),
                         t.GetNetname(), 'track'))
    smd = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            lys = tuple(ly for ly in CU if p.IsOnLayer(ly))
            if not lys and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue                         # paste-only apertures of an exposed pad
            obst.append(('r', lys or CU, r, p.GetNetname(), fp.GetReference() + '.' + p.GetNumber()))
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and lys:
                smd.append((r, fp.GetReference() + '.' + p.GetNumber(), p.GetNetname()))
    new = []
    for net, ly, w, pts in T:
        for a, e in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(e[0] - a[0], e[1] - a[1]) / 0.04))
            for k in range(n + 1):
                new.append((net, (ly,), (a[0] + (e[0] - a[0]) * k / n, a[1] + (e[1] - a[1]) * k / n), w / 2,
                            'T %s %s' % (net, board.GetLayerName(ly))))
    vias = [(net, q, d, dr) for net, q, d, dr in V]
    for a, e in MV:
        for t in board.GetTracks():
            if t.GetClass() == 'PCB_VIA' and near(xy(t.GetPosition()), a):
                vias.append((t.GetNetname(), e, mm(t.GetWidth(pcbnew.F_Cu)), mm(t.GetDrill())))
                for u in board.GetTracks():       # the tracks that follow the via
                    if u.GetClass() != 'PCB_VIA' and u.GetNetname() == t.GetNetname() and not doomed(u):
                        s0, s1 = xy(u.GetStart()), xy(u.GetEnd())
                        if near(s0, a) or near(s1, a):
                            p, q = moved(s0), moved(s1)
                            n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / 0.04))
                            for k in range(n + 1):
                                new.append((u.GetNetname(), (u.GetLayer(),), (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n),
                                            mm(u.GetWidth()) / 2, 'moved track %s' % u.GetNetname()))
    bad = 0
    for net, q, d, dr in vias:
        new.append((net, CU, q, d / 2, 'V %s' % net))
        for r, ref, pnet in smd:
            if pnet == net and (r[2] - r[0]) * (r[3] - r[1]) > 4:
                continue                         # thermal / ground vias in an exposed pad of the same net
            if rect_d(q, r) < dr / 2:
                print('  via hole at %.2f, %.2f is on pad %s' % (q[0], q[1], ref)); bad += 1
            elif rect_d(q, r) < d / 2 and ref:
                pass
        for c, hr in holes:
            g = math.hypot(c[0] - q[0], c[1] - q[1])
            if 0.01 < g < hr + dr / 2 + 0.2:
                print('  via hole at %.2f, %.2f is %.2f mm from the hole at %.2f, %.2f' % (q[0], q[1], g - hr - dr / 2, c[0], c[1])); bad += 1
    worst = {}
    for net, lys, p, r, lab in new:
        for kind, olys, g, onet, olab in obst:
            if onet == net or not set(lys) & set(olys):
                continue
            if kind == 'c':
                d = math.hypot(p[0] - g[0], p[1] - g[1]) - g[2]
            elif kind == 's':
                if abs(p[0] - g[0][0]) > 30 and abs(p[0] - g[1][0]) > 30:
                    continue
                d = seg_d(p, g[0], g[1]) - g[2]
            else:
                d = rect_d(p, g)
            d -= r
            if d < need:
                key = (lab, olab, onet)
                if key not in worst or d < worst[key][0]:
                    worst[key] = (d, p)
    for key, (d, p) in sorted(worst.items(), key=lambda kv: kv[1][0]):
        print('  %5.2f mm  %-26s at %.2f, %.2f  <->  %s %s' % (d, key[0], p[0], p[1], key[1], key[2]))
    print('conflicts:', len(worst) + bad)
    return len(worst) + bad


mode = sys.argv[2]
if mode == 'check':
    bad = check()
    sys.stdout.flush()
    os._exit(1 if bad else 0)       # a script can stop on conflicts
elif mode == 'rm':
    kill = [t for t in board.GetTracks() if doomed(t)]
    for t in kill:
        board.Remove(t)
    print('removed', len(kill), 'of', len(RM) + len(RMVIA))
    for ref, deg in ROT:
        fp = [x for x in board.GetFootprints() if x.GetReference() == ref][0]
        fp.SetOrientationDegrees((fp.GetOrientationDegrees() + deg) % 360)
        print(ref, 'turned to', fp.GetOrientationDegrees())
    board.Save(PCB)
elif mode == 'add':
    for a, e in MV:
        n = 0
        for t in board.GetTracks():
            if t.GetClass() == 'PCB_VIA':
                if near(xy(t.GetPosition()), a):
                    t.SetPosition(pcbnew.VECTOR2I(F(e[0]), F(e[1]))); n += 1
            else:
                if near(xy(t.GetStart()), a):
                    t.SetStart(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
                if near(xy(t.GetEnd()), a):
                    t.SetEnd(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
        print('via moved' if n else 'NO VIA at %.2f, %.2f' % a)
    for net, ly, w, pts in T:
        for a, e in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1]))); t.SetEnd(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
            t.SetWidth(F(w)); t.SetLayer(ly); t.SetNet(board.FindNet(net))
            board.Add(t)
    for net, q, d, dr in V:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(F(q[0]), F(q[1]))); v.SetWidth(pcbnew.F_Cu, F(d)); v.SetDrill(F(dr))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(board.FindNet(net))
        board.Add(v)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print('added %d track runs, %d vias' % (len(T), len(V)))
sys.stdout.flush()
os._exit(0)
