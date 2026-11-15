"""Turn "track end lies on the body of another track" joints into real end-to-end joints.

DRC reports a track end as dangling when it lands somewhere along another track instead of on one of its
end points (or on a pad / via). The copper is connected, but the joint is fragile. For every such end the
other track is split at that point and the end is snapped onto its centre line, so both now share an end
point. No copper is added or removed; halves of a locked track stay locked.

Usage: python fix_dangling.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
segs = [t for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
uid = lambda t: t.m_Uuid.AsString()


def anchored(t, q):
    """True if q (an end of t) sits on a pad, a via or an end point of another track of the same net."""
    net = t.GetNetname()
    if any(p.GetNetname() == net and p.IsOnLayer(t.GetLayer()) and p.HitTest(q) for p in pads):
        return True
    if any(v.GetNetname() == net and v.HitTest(q) for v in vias):
        return True
    return any(o.GetNetname() == net and o.GetLayer() == t.GetLayer() and uid(o) != uid(t)
               and (o.GetStart() == q or o.GetEnd() == q) for o in segs)


def host(t, q):
    """Another track of the same net and layer whose body (not an end) contains q."""
    for o in segs:
        if o.GetNetname() == t.GetNetname() and o.GetLayer() == t.GetLayer() and uid(o) != uid(t) \
                and o.GetStart() != q and o.GetEnd() != q and o.GetLength() > 0 and o.HitTest(q):
            return o
    return None


split = 0
for t in list(segs):
    for which in ('S', 'E'):
        q = t.GetStart() if which == 'S' else t.GetEnd()
        if anchored(t, q):
            continue
        o = host(t, q)
        if o is None:
            continue
        a, e = o.GetStart(), o.GetEnd()
        dx, dy = e.x - a.x, e.y - a.y
        k = ((q.x - a.x) * dx + (q.y - a.y) * dy) / float(dx * dx + dy * dy)
        k = min(max(k, 0.0), 1.0)
        c = pcbnew.VECTOR2I(int(round(a.x + k * dx)), int(round(a.y + k * dy)))
        if which == 'S':
            t.SetStart(c)
        else:
            t.SetEnd(c)
        if c != a and c != e:
            n = pcbnew.PCB_TRACK(board)
            n.SetStart(c); n.SetEnd(e); n.SetWidth(o.GetWidth()); n.SetLayer(o.GetLayer()); n.SetNet(o.GetNet())
            n.SetLocked(o.IsLocked())
            o.SetEnd(c)
            board.Add(n)
            segs.append(n)
        split += 1
        print('%-24s joint at (%.3f, %.3f)' % (t.GetNetname()[-24:], pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)))
# zero-length leftovers
gone = 0
for t in list(segs):
    if t.GetLength() == 0:
        board.Remove(t)
        gone += 1
# Pure stubs: an end that touches nothing of its net at all (no pad, via, zone fill, track end or track body).
# With every body joint converted above, such a segment carries no connection and can go, locked or not.
zones = list(board.Zones())


def free(t, q):
    net, lay = t.GetNetname(), t.GetLayer()
    half = t.GetWidth() // 2          # the copper of the track end reaches this far: overlap counts as contact
    if any(p.GetNetname() == net and p.IsOnLayer(lay) and p.HitTest(q, half) for p in pads):
        return False
    if any(v.GetNetname() == net and v.HitTest(q, half) for v in vias):
        return False
    if any(z.GetNetname() == net and z.IsOnLayer(lay) and z.HitTestFilledArea(lay, q) for z in zones):
        return False
    return not any(o.GetNetname() == net and o.GetLayer() == lay and uid(o) != uid(t) and o.HitTest(q, half)
                   for o in segs)


stubs = 0
again = True
while again:
    again = False
    for t in list(segs):
        if t.GetLength() == 0:
            continue
        # a via or pad of the net sitting on the body (not on an end) still makes the segment a connection
        on_body = any(v.GetNetname() == t.GetNetname() and t.HitTest(v.GetPosition()) for v in vias) or             any(p.GetNetname() == t.GetNetname() and p.IsOnLayer(t.GetLayer()) and t.HitTest(p.GetPosition())
                for p in pads)
        if not on_body and (free(t, t.GetStart()) or free(t, t.GetEnd())):
            print('stub removed: %-22s %.3f mm at (%.3f, %.3f)%s' % (
                t.GetNetname()[-22:], pcbnew.ToMM(t.GetLength()), pcbnew.ToMM(t.GetStart().x),
                pcbnew.ToMM(t.GetStart().y), ' [locked]' if t.IsLocked() else ''))
            board.Remove(t)
            segs.remove(t)
            stubs += 1
            again = True
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('joints fixed', split, '| zero-length segments removed', gone, '| stubs removed', stubs)
sys.stdout.flush()
os._exit(0)
