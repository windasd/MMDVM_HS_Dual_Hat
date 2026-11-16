"""Move vias off SMD pads (run with KiCad's python).

The autorouter and the ground stitching drop vias on pads. Without plugged vias (not part of the standard
JLCPCB process) the hole draws solder away from the joint. For every via whose hole touches an SMD pad the
nearest spot is searched where the whole via is off every pad and clear of other nets on all layers; the via
moves there, a short track joins it to the pad and the tracks that ended on it on other layers are extended.

Usage: python via_out_of_pad.py [--dry] [--locked]      (--locked: also move locked vias)
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
mm, F = pcbnew.ToMM, pcbnew.FromMM
CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
HOLE_GAP = 0.25
CL = float(os.environ.get('VOP_CL', '0.13'))            # via copper to other nets
PAD_GAP = float(os.environ.get('VOP_PADGAP', '0.1'))     # via copper to the pads of its own net
REACH = float(os.environ.get('VOP_REACH', '2.0'))        # search radius, mm
DRY, LOCKED = '--dry' in sys.argv, '--locked' in sys.argv
board = pcbnew.LoadBoard(PCB)


def seg_d(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L = dx * dx + dy * dy
    k = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def rect_d(p, r):
    return math.hypot(max(r[0] - p[0], 0.0, p[0] - r[2]), max(r[1] - p[1], 0.0, p[1] - r[3]))


def xy(v):
    return (mm(v.x), mm(v.y))


pads = []           # (rect, layers, net, smd, hole radius, centre, ref)
for fp in board.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
        smd = p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
        pads.append((r, tuple(ly for ly in CU if p.IsOnLayer(ly)) or CU, p.GetNetname(), smd,
                     0.0 if smd else mm(p.GetDrillSize().x) / 2, xy(p.GetPosition()), fp.GetReference() + '.' + p.GetNumber(), p))
rules = [z for z in board.Zones() if z.GetIsRuleArea()]
POLY = [(M.X0 + x, M.Y0 - y) for x, y in M.OUTLINE]


def edge_dist(x, y):
    d = 1e9
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        d = min(d, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return d


def on_pad(t):
    c, r = xy(t.GetPosition()), mm(t.GetDrill()) / 2
    for pd in pads:
        if pd[3] and rect_d(c, pd[0]) < r and pd[7].HitTest(t.GetPosition(), t.GetDrill() // 2):
            return pd
    return None


TRK, VIA = [], []           # plain copies of the copper: the search below runs on these
for t in board.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        VIA.append([t, t.GetNetname(), xy(t.GetPosition()), mm(t.GetWidth(pcbnew.F_Cu)) / 2, mm(t.GetDrill()) / 2])
    else:
        TRK.append((t.GetNetname(), t.GetLayer(), xy(t.GetStart()), xy(t.GetEnd()), mm(t.GetWidth()) / 2))


class Local:
    """Everything within reach of one via."""

    def __init__(self, me, c):
        lim = REACH + 2.5
        self.trk = [k for k in TRK if min(k[2][0], k[3][0]) - lim < c[0] < max(k[2][0], k[3][0]) + lim
                    and min(k[2][1], k[3][1]) - lim < c[1] < max(k[2][1], k[3][1]) + lim]
        self.via = [k for k in VIA if k is not me and abs(k[2][0] - c[0]) < lim and abs(k[2][1] - c[1]) < lim]
        self.pad = [k for k in pads if rect_d(c, k[0]) < lim]


def clear_point(q, rad, layers, net, loc, need=CL):
    """A disc of radius rad at q on these layers against copper of other nets."""
    for onet, c, r in ((k[1], k[2], k[3]) for k in loc.via):
        if onet != net and math.hypot(c[0] - q[0], c[1] - q[1]) - r - rad < need:
            return False
    for onet, ly, a, e, hw in loc.trk:
        if onet != net and ly in layers and seg_d(q, a, e) - hw - rad < need:
            return False
    for r, lys, pnet, smd, hole, c, ref, p in loc.pad:
        if pnet != net and set(lys) & set(layers) and rect_d(q, r) - rad < need:
            return False
    return True


def clear_seg(a, e, w, layer, net, loc):
    n = max(1, int(math.hypot(e[0] - a[0], e[1] - a[1]) / 0.05))
    return all(clear_point((a[0] + (e[0] - a[0]) * k / n, a[1] + (e[1] - a[1]) * k / n), w / 2, (layer,), net, loc, 0.1)
               for k in range(n + 1))


def via_spot_ok(q, v, net, loc):
    rad, hole = mm(v.GetWidth(pcbnew.F_Cu)) / 2, mm(v.GetDrill()) / 2
    if edge_dist(*q) < rad + 0.35:
        return False
    for r, lys, pnet, smd, phole, c, ref, p in loc.pad:     # off every SMD pad, also of its own net
        if smd and rect_d(q, r) < rad + PAD_GAP:
            return False
        if phole and math.hypot(c[0] - q[0], c[1] - q[1]) < phole + hole + HOLE_GAP:
            return False
    for k in loc.via:
        if math.hypot(k[2][0] - q[0], k[2][1] - q[1]) < k[4] + hole + HOLE_GAP:
            return False
    if not clear_point(q, rad, CU, net, loc):
        return False
    pt = pcbnew.VECTOR2I(F(q[0]), F(q[1]))
    return not any(z.Outline().Contains(pt) for z in rules)


todo = []
for k in VIA:
    if LOCKED or not k[0].IsLocked():
        pd = on_pad(k[0])
        if pd:
            todo.append((k, pd))
moved, stuck = 0, []
for me, pd in todo:
    v, net, c = me[0], me[1], me[2]
    loc = Local(me, c)
    ends = {}                                   # layer -> width of the tracks that end on the via
    for onet, ly, a, e, hw in loc.trk:
        if onet == net and min(math.hypot(a[0] - c[0], a[1] - c[1]), math.hypot(e[0] - c[0], e[1] - c[1])) < 0.03:
            ends[ly] = min(ends.get(ly, 9.9), hw * 2)
    pad_layer = [ly for ly in pd[1] if ly in (pcbnew.F_Cu, pcbnew.B_Cu)][0]
    r = pd[0]
    wpad = max(0.2, min(0.4, round(min(r[2] - r[0], r[3] - r[1]) - 0.001, 2)))
    if net != 'GND' and not net.startswith('+') and net not in ('VSYS', 'CELL+', 'SYS_DCIN'):
        wpad = min(wpad, 0.25)
    best, N = None, int(REACH / 0.05)
    cands = sorted(((dx * 0.05, dy * 0.05) for dx in range(-N, N + 1) for dy in range(-N, N + 1)
                    if 0.2 < math.hypot(dx, dy) * 0.05 <= REACH), key=lambda d: math.hypot(*d))
    for dx, dy in cands:
        q = (round(c[0] + dx, 3), round(c[1] + dy, 3))
        if not via_spot_ok(q, v, net, loc):
            continue
        # join to the pad: straight to the old spot if that is free, else to the nearest point of the pad
        tgt = [c, (min(max(q[0], r[0] + wpad / 2), r[2] - wpad / 2), min(max(q[1], r[1] + wpad / 2), r[3] - wpad / 2))]
        join = [(g, w) for w in (wpad, 0.2) for g in tgt if clear_seg(q, g, w, pad_layer, net, loc)]
        if not join:
            continue
        join, wj = [join[0][0]], join[0][1]
        if not all(clear_seg(q, c, w, ly, net, loc) for ly, w in ends.items() if ly != pad_layer):
            continue
        if join[0] is not c and pad_layer in ends and not clear_seg(q, c, ends[pad_layer], pad_layer, net, loc):
            continue
        best = (q, join[0], wj)
        break
    if not best:
        stuck.append('%s (%s) at %.2f, %.2f' % (pd[6], net, c[0], c[1]))
        continue
    q, g, wj = best
    print('%-9s %-20s via %.2f, %.2f -> %.2f, %.2f (%.2f mm)%s' % (
        pd[6], net, c[0], c[1], q[0], q[1], math.hypot(q[0] - c[0], q[1] - c[1]),
        '  + tracks on ' + ', '.join(board.GetLayerName(ly) for ly in ends if ly != pad_layer) if set(ends) - {pad_layer} else ''))
    moved += 1
    me[2] = q
    if DRY:
        continue
    v.SetPosition(pcbnew.VECTOR2I(F(q[0]), F(q[1])))
    segs = [(pad_layer, wj, q, g)] + [(ly, w, q, c) for ly, w in ends.items() if ly != pad_layer]
    if g is not c and pad_layer in ends:
        segs.append((pad_layer, ends[pad_layer], q, c))
    for ly, w, a, e in segs:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
        t.SetWidth(F(w))
        t.SetLayer(ly)
        t.SetNet(v.GetNet())
        t.SetLocked(v.IsLocked())
        board.Add(t)
        TRK.append((net, ly, a, e, w / 2))
print('vias on pads: %d, moved: %d' % (len(todo), moved))
for s in stuck:
    print('NO SPOT:', s)
if not DRY:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
sys.stdout.flush()
os._exit(0)
