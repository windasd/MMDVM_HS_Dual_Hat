"""Beef up the high-current nets after autorouting (run with KiCad's python).

1. Every unlocked track segment of a power net is widened to the largest width in its list that keeps
   the clearance to other nets, holes and the board edge (checked by sampling along the segment).
2. A VSYS pour is added on In2 over the power zone (it ties the VSYS vias together under the converters).

Usage: python widen_power.py
"""
import math
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
CL = 0.15                                   # clearance kept to other nets (rule minimum is 0.1)
EDGE = 0.35
HIGH = (1.5, 1.2, 1.0, 0.8, 0.6, 0.5)       # battery / converter currents (up to ~5-7 A)
MID = (0.8, 0.6, 0.5)                       # 5 V, 3.5 V rails (< 2 A)
NETS = {}
for n in ('VSYS', 'VBUS', 'CELL+', 'CELL-', '+12V_BOOST', '+12V_SENSE', 'SYS_DCIN', '/Power/CELL1+',
          '/Power/CELL2+', '/Power/CELL3+', '/Power/CELL4+', '/Power/B12_SW', '/Power/B12_VOUT', '/Power/BQ_SW',
          '/Power/BQ_PMID', '/Power/PROT_MID'):
    NETS[n] = HIGH
for n in ('+5V', '+3V5', '/Power/B5_SW', '/Power/BB_L1', '/Power/BB_L2', 'MESH_VBAT_NRF', '+3V3_ETH', '+1V2_ETH',
          '/Ethernet/ETH_SW33', '/Ethernet/ETH_SW12'):
    NETS[n] = MID

# Ethernet controller rails: finer steps, the escapes between 0.5 mm pitch pins cannot take 0.5 mm
ETHW = (0.8, 0.6, 0.5, 0.4, 0.3, 0.25)
for n in ('+3V3_ETH', '+1V2_ETH', '/Ethernet/ETH_VDD12A', '/Ethernet/ETH_VDD12PLL', '/Ethernet/ETH_VDD12USBPLL',
          '/Ethernet/ETH_VDD33A', '/Ethernet/ETH_VMAG'):
    NETS[n] = ETHW
obst = []     # (bbox x0, y0, x1, y1, object, net, layers or None for all)
for fp in board.GetFootprints():
    for p in fp.Pads():
        b = p.GetBoundingBox()
        through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        lay = None if through else (pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
        obst.append((b.GetX(), b.GetY(), b.GetX() + b.GetWidth(), b.GetY() + b.GetHeight(), p, p.GetNetname(), lay))
for t in board.GetTracks():
    b = t.GetBoundingBox()
    lay = None if t.GetClass() == 'PCB_VIA' else t.GetLayer()
    obst.append((b.GetX(), b.GetY(), b.GetX() + b.GetWidth(), b.GetY() + b.GetHeight(), t, t.GetNetname(), lay))


def edge_ok(q, half):
    x, y = M.model(q)
    poly = M.OUTLINE
    lim = half + EDGE
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if x1 == x2 and min(y1, y2) - lim <= y <= max(y1, y2) + lim and abs(x - x1) < lim:
            return False
        if y1 == y2 and min(x1, x2) - lim <= x <= max(x1, x2) + lim and abs(y - y1) < lim:
            return False
    return True


def fits(t, w):
    a, e = t.GetStart(), t.GetEnd()
    half = w / 2
    reach = mm(half + CL)
    pre = reach + mm(1.0)             # obstacles may have been widened since their bbox was recorded
    x0, x1 = min(a.x, e.x) - pre, max(a.x, e.x) + pre
    y0, y1 = min(a.y, e.y) - pre, max(a.y, e.y) + pre
    near = [o for o in obst if o[5] != t.GetNetname() and (o[6] is None or o[6] == t.GetLayer())
            and o[0] <= x1 and o[2] >= x0 and o[1] <= y1 and o[3] >= y0]
    n = max(1, int(math.hypot(a.x - e.x, a.y - e.y) / mm(0.1)))
    for j in range(n + 1):
        q = pcbnew.VECTOR2I(int(a.x + (e.x - a.x) * j / n), int(a.y + (e.y - a.y) * j / n))
        if not edge_ok(q, half):
            return False
        for o in near:
            if o[4].HitTest(q, reach):
                return False
    return True


stats = {}
for t in board.GetTracks():
    if t.GetClass() != 'PCB_TRACK' or t.IsLocked() or t.GetNetname() not in NETS:
        continue
    cur = pcbnew.ToMM(t.GetWidth())
    for w in NETS[t.GetNetname()]:
        if w <= cur + 1e-6:
            break
        if fits(t, w):
            t.SetWidth(mm(w))
            cur = w
            break
    s = stats.setdefault(t.GetNetname(), [0, 0.0, 0.0, 9.9])
    length = pcbnew.ToMM(t.GetLength())
    s[0] += 1
    s[1] += length
    s[2] += length * cur
    s[3] = min(s[3], cur)
print('%-18s %5s %8s %9s %6s' % ('net', 'segs', 'len mm', 'avg w mm', 'min w'))
for n, (c, ln, lw, mn) in sorted(stats.items()):
    print('%-18s %5d %8.1f %9.2f %6.2f' % (n.split('/')[-1], c, ln, lw / max(ln, 1e-9), mn))

# ---- VSYS pour on In2 over the power zone (remove an older one first)
for z in list(board.Zones()):
    if z.GetNetname() == 'VSYS':
        board.Remove(z)
zx0, zy0, zx1, zy1 = M.ZONES['Power']
z = pcbnew.ZONE(board)
z.SetLayer(pcbnew.In2_Cu)
z.SetNet(board.FindNet('VSYS'))
ol = z.Outline()
ol.NewOutline()
for (x, y) in ((zx0, zy0), (zx1, zy0), (zx1, zy1 + 6.0), (zx0, zy1 + 6.0)):
    ol.Append(mm(M.X0 + x), mm(M.Y0 - y))
z.SetLocalClearance(mm(0.2))
z.SetMinThickness(mm(0.25))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
z.SetAssignedPriority(1)
board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
print('VSYS pour on In2: %.0f mm2' % (z.GetFilledArea() / 1e12))
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
