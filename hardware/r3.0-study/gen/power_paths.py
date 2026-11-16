"""Report the copper between the pads of the high-current paths (run with KiCad's python).

For each (net, from, to, amps) the lowest-resistance single chain of tracks and vias is found on the track
graph of that net (zone fills are not counted, so nets with a pour are better than reported). Printed: length,
narrowest width, vias, resistance (1 oz outer 0.49 mohm/sq, 0.5 oz inner 0.98 mohm/sq, via 2.4 mohm), drop
and loss at the given current. A trace is flagged when it is narrower than IPC-2221 allows for a 20 K rise.

Usage: python power_paths.py
"""
import heapq
import math
import os
import sys
from collections import defaultdict

import pcbnew

import main_pcb as M

PATHS = [  # net, from, to, A
    ('/Power/CELL1+', 'BT100.1', 'F100.1', 2.5), ('/Power/CELL2+', 'BT101.1', 'F101.1', 2.5),
    ('/Power/CELL3+', 'BT102.1', 'F102.1', 2.5), ('/Power/CELL4+', 'BT103.1', 'F103.1', 2.5),
    ('CELL+', 'F100.2', 'U101.13', 2.5), ('CELL+', 'F101.2', 'U101.13', 2.5),
    ('CELL+', 'F102.2', 'U101.13', 2.5), ('CELL+', 'F103.2', 'U101.13', 2.5),
    ('CELL-', 'BT100.2', 'Q100.1', 2.5), ('CELL-', 'BT101.2', 'Q100.1', 2.5),
    ('CELL-', 'BT102.2', 'Q100.1', 2.5), ('CELL-', 'BT103.2', 'Q100.1', 2.5),
    ('/Power/PROT_MID', 'Q100.5', 'Q101.5', 10.0),
    ('VSYS', 'U101.15', 'L101.1', 9.0), ('VSYS', 'U101.15', 'L102.1', 1.5), ('VSYS', 'U101.15', 'U108.5', 0.5),
    ('VSYS', 'L100.2', 'U101.15', 3.0),
    ('/Power/B12_SW', 'L101.2', 'U104.7', 9.0), ('/Power/B12_VOUT', 'U104.8', 'Q102.1', 2.5),
    ('+12V_BOOST', 'Q102.5', 'R115.1', 2.5), ('+12V_SENSE', 'R115.2', 'Q103.1', 2.5),
    ('SYS_DCIN', 'Q103.5', 'J1.36', 2.5), ('VBUS', 'J100.A4', 'U101.1', 3.0),
    ('/Power/BQ_SW', 'U101.19', 'L100.1', 3.0), ('+5V', 'U107.3', 'J5.4', 0.5), ('+5V', 'U107.3', 'U62.4', 0.4),
    ('/Power/B5_SW', 'L102.2', 'U107.2', 2.0), ('+3V5', 'U108.1', 'U110.1', 0.3),
    # LAN7500: 1.2 V core about 0.4 A in all, 3.3 V about 0.3 A in all; per pin taken as half the rail
    ('+1V2_ETH', 'L65.2', 'U60.8', 0.2), ('+1V2_ETH', 'L65.2', 'U60.11', 0.2), ('+1V2_ETH', 'L65.2', 'U60.20', 0.2),
    ('+1V2_ETH', 'L65.2', 'U60.23', 0.2), ('+1V2_ETH', 'L65.2', 'U60.30', 0.2), ('+1V2_ETH', 'L65.2', 'U60.36', 0.2),
    ('+1V2_ETH', 'L65.2', 'U60.49', 0.2),
    ('+3V3_ETH', 'L64.2', 'U60.7', 0.15), ('+3V3_ETH', 'L64.2', 'U60.19', 0.15), ('+3V3_ETH', 'L64.2', 'U60.24', 0.15),
    ('+3V3_ETH', 'L64.2', 'U60.37', 0.15),
]
RSQ = {pcbnew.F_Cu: 0.49e-3, pcbnew.B_Cu: 0.49e-3}
R_INNER, R_VIA = 0.98e-3, 2.4e-3
mm = pcbnew.ToMM
board = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb'))


def ipc_width(amps, outer=True, dt=20.0, oz=1.0):
    area = (amps / ((0.048 if outer else 0.024) * dt ** 0.44)) ** (1 / 0.725)      # mil^2
    return area / (oz * 1.378) * 0.0254


def key(p, layer):
    return (round(mm(p.x), 2), round(mm(p.y), 2), layer)


graphs = {}


def graph(net):
    if net in graphs:
        return graphs[net]
    g = defaultdict(list)
    trk = [t for t in board.GetTracks() if t.GetNetname() == net]
    for t in trk:
        if t.GetClass() == 'PCB_VIA':
            ks = [key(t.GetPosition(), ly) for ly in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)]
            for a in ks:
                for c in ks:
                    if a != c:
                        g[a].append((c, R_VIA, 0.0, 9.9, 1))
        else:
            a, c = key(t.GetStart(), t.GetLayer()), key(t.GetEnd(), t.GetLayer())
            w, ln = mm(t.GetWidth()), mm(t.GetLength())
            r = RSQ.get(t.GetLayer(), R_INNER) * ln / w
            g[a].append((c, r, ln, w, 0)); g[c].append((a, r, ln, w, 0))
    # track ends inside a pad (or a via on it) are joined to the pad node at no cost
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net:
                continue
            pk = ('PAD', fp.GetReference() + '.' + p.GetNumber())
            for k in list(g):
                # 0.3 mm slack: a wide track may overlap the pad without its end point being inside it
                if k[0] != 'PAD' and p.IsOnLayer(k[2]) and p.HitTest(
                        pcbnew.VECTOR2I(pcbnew.FromMM(k[0]), pcbnew.FromMM(k[1])), pcbnew.FromMM(0.3)):
                    g[pk].append((k, 0.0, 0.0, 9.9, 0)); g[k].append((pk, 0.0, 0.0, 9.9, 0))
            if pk not in g:         # pad in the middle of a wide segment (a bar running over a contact)
                c = p.GetPosition()
                for t in trk:
                    if t.GetClass() != 'PCB_VIA' and p.IsOnLayer(t.GetLayer()) and (
                            t.HitTest(c) or t.HitTest(p.GetBoundingBox(), False)):     # bar over part of the pad
                        for e in (t.GetStart(), t.GetEnd()):
                            k = key(e, t.GetLayer())
                            ln = math.hypot(mm(c.x) - k[0], mm(c.y) - k[1]); w = mm(t.GetWidth())
                            r = RSQ.get(t.GetLayer(), R_INNER) * ln / w
                            g[pk].append((k, r, ln, w, 0)); g[k].append((pk, r, ln, w, 0))
    # T-junctions: a track end that lies on the body of another segment
    segs = [t for t in trk if t.GetClass() != 'PCB_VIA']
    nodes = [k for k in g if k[0] != 'PAD']
    for t in segs:
        a = key(t.GetStart(), t.GetLayer())
        on = [k for k in nodes if k[2] == t.GetLayer() and t.HitTest(
            pcbnew.VECTOR2I(pcbnew.FromMM(k[0]), pcbnew.FromMM(k[1])))]
        on.sort(key=lambda k: math.hypot(k[0] - a[0], k[1] - a[1]))      # chained in order along the segment
        w = mm(t.GetWidth())
        for k, c in zip(on, on[1:]):
            ln = math.hypot(k[0] - c[0], k[1] - c[1])
            r = RSQ.get(t.GetLayer(), R_INNER) * ln / w
            g[k].append((c, r, ln, w, 0)); g[c].append((k, r, ln, w, 0))
    graphs[net] = g
    return g


zoned = {z.GetNetname() for z in board.Zones() if not z.GetIsRuleArea()}
print('%-16s %-9s %-9s %4s | %6s %5s %4s %7s %6s %6s' % ('net', 'from', 'to', 'A', 'mm', 'min w', 'vias', 'mohm', 'mV', 'mW'))
for net, a, c, amps in PATHS:
    g = graph(net)
    src, dst = ('PAD', a), ('PAD', c)
    best = {src: 0.0}; prev = {}; pq = [(0.0, 0, src)]; n = 0
    while pq:
        d, _, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > best.get(u, 1e9):
            continue
        for v, r, ln, w, via in g[u]:
            if d + r < best.get(v, 1e9):
                best[v] = d + r; prev[v] = (u, ln, w, via); n += 1
                heapq.heappush(pq, (d + r, n, v))
    if dst not in best:
        print('%-16s %-9s %-9s %4.1f | no track chain%s' % (net[-16:], a, c, amps, ' (net has a pour)' if net in zoned else ''))
        continue
    ln = 0.0; wmin = 9.9; vias = 0; u = dst; narrow = 0.0
    need = ipc_width(amps)
    while u != src:
        u, l_, w_, v_ = prev[u]
        ln += l_; vias += v_
        if l_ > 0:
            wmin = min(wmin, w_)
            if w_ < need:
                narrow += l_
    r = best[dst]
    print('%-16s %-9s %-9s %4.1f | %6.1f %5.2f %4d %7.1f %6.0f %6.0f %s' % (
        net[-16:], a, c, amps, ln, wmin, vias // 2 if vias else 0, r * 1e3, r * amps * 1e3, r * amps * amps * 1e3,
        ('<-- %.1f mm narrower than %.2f mm (IPC-2221, 20 K)' % (narrow, need)) if narrow > 0.05 else '')
          + (' [pour]' if net in zoned else ''))
sys.stdout.flush()
os._exit(0)
