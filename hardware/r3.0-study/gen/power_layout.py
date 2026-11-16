"""Re-place the power section of the routed main board around its current paths (run with KiCad python).

The grid placement of main_pcb.py scatters each converter over the power zone; power_paths.py shows the result
(9 A through 20 mm of 0.4 mm track). This script works on the routed board:

  python power_layout.py place    move the parts: FIX = hand-placed power stages, NEAR = small parts dropped
                                  at the nearest free spot to a target (courtyards and copper channels kept clear)
  python power_layout.py rip      remove the tracks that the new placement invalidates
  python power_layout.py copper   draw the high-current copper (wide locked tracks, via arrays)

Coordinates are board coordinates in mm as shown in the PCB editor. Afterwards: reroute_prep.py, Freerouting,
route.py import and the usual clean-up; power_paths.py checks the result.
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
mm, F = pcbnew.ToMM, pcbnew.FromMM
BOX = (143.3, 115.6, 187.7, 176.2)          # everything inside is re-routed
LIMIT = (143.6, 106.5, 187.3, 178.8)        # NEAR parts stay inside
CELL_Y = {4: 118.7, 3: 140.5, 2: 162.3, 1: 184.1}
FUSE_Y = {'F103': 118.7, 'F102': 130.0, 'F101': 159.6, 'F100': 172.6}   # clear of the USB stitching vias
FUSE_X = 148.6
FIX = {
    # fuses at the end of the cell bars (B.Cu), pad 1 = cell, pad 2 = CELL+ collector (B.Cu, x 150.7 .. 155.3)
    'F103': (FUSE_X, 118.7, 0), 'F102': (FUSE_X, 130.0, 0), 'F101': (FUSE_X, 159.6, 0), 'F100': (FUSE_X, 172.6, 0),
    # charger: BAT / SYS pins face the VSYS bus (south), SW pins face the inductor (east)
    'U101': (158.6, 154.2, 270), 'L100': (166.4, 155.6, 0),
    # 12 V boost, left to right: inductor, converter, output capacitors, load switch, bulk; second row back to
    # the shunt and the ideal diode, whose drain drops to B.Cu towards the host connector
    'L101': (160.4, 169.9, 0), 'U104': (169.3, 165.7, 90), 'C119': (173.0, 165.7, 270), 'C120': (175.6, 165.7, 270),
    'Q102': (179.8, 164.9, 0), 'C122': (183.5, 164.9, 270), 'C124': (186.1, 164.9, 270),
    'R115': (181.5, 169.8, 180), 'Q103': (176.2, 170.4, 180), 'C123': (184.6, 172.9, 0),
    'C113': (161.2, 161.9, 0), 'C114': (165.0, 161.9, 0), 'C108': (160.4, 158.0, 0),
    # cell protection on the CELL- bar (B.Cu, x 179.4 .. 186.4)
    'Q100': (182.6, 130.0, 180), 'Q101': (177.2, 130.0, 0),
    # 5 V boost and 3.5 V buck-boost beside the VSYS bus
    'L102': (174.6, 158.5, 0), 'U107': (179.4, 158.5, 0), 'C129': (179.9, 161.2, 0), 'C130': (183.7, 161.2, 0),
    'U108': (178.0, 153.3, 0), 'L103': (173.3, 153.3, 90),
}
NEAR = [   # ref, target x, y, preferred rotation
    ('C103', 163.4, 150.6, 0), ('C104', 168.6, 150.6, 0), ('C105', 162.2, 153.9, 90), ('C106', 163.0, 148.6, 0),
    ('C109', 154.2, 153.3, 90), ('C110', 154.2, 149.6, 90), ('R102', 155.4, 151.6, 0), ('R104', 154.6, 147.2, 0),
    ('R103', 156.6, 147.2, 0), ('TH100', 155.5, 145.6, 0), ('D102', 153.3, 144.0, 0), ('R106', 157.3, 150.8, 90),
    ('D101', 158.6, 150.2, 90), ('R105', 158.6, 148.0, 90),
    ('C115', 168.0, 162.9, 0), ('R122', 170.2, 162.9, 0), ('C116', 169.0, 161.5, 0), ('R114', 172.4, 162.4, 0),
    ('C121', 172.4, 161.2, 0), ('R109', 167.6, 168.7, 0), ('R110', 167.6, 169.8, 0), ('C118', 167.6, 170.9, 0),
    ('R111', 167.6, 172.0, 0), ('C117', 167.6, 173.1, 0), ('R113', 167.6, 174.2, 0), ('R112', 170.0, 173.3, 0),
    ('U106', 176.3, 174.6, 0), ('C126', 179.2, 174.6, 0), ('C127', 171.6, 176.6, 0), ('U105', 185.2, 156.6, 90),
    ('R116', 181.6, 157.9, 90), ('R117', 182.7, 157.9, 90),
    ('C131', 181.0, 153.0, 90), ('R118', 182.1, 153.0, 90), ('R119', 180.6, 150.8, 0), ('R120', 182.6, 150.8, 0),
    ('C133', 175.6, 149.9, 0), ('C134', 179.2, 149.4, 0), ('C132', 181.2, 155.4, 0), ('C128', 184.2, 152.8, 90),
    ('U109', 172.6, 146.2, 0), ('U110', 178.6, 145.8, 0), ('C135', 175.6, 147.6, 0), ('C137', 181.6, 147.6, 0),
    ('C138', 181.6, 144.6, 0), ('C139', 181.6, 143.0, 0),
    ('U102', 180.0, 125.6, 0), ('R107', 182.6, 125.6, 0), ('C111', 182.6, 126.8, 0), ('R108', 178.0, 125.6, 0),
    ('R130', 185.3, 127.6, 0), ('R131', 174.9, 132.6, 0),
    ('U103', 157.6, 122.4, 0), ('C112', 157.6, 120.0, 0),
    ('U100', 166.0, 137.4, 0), ('R100', 171.6, 135.6, 0), ('R101', 171.6, 138.6, 90), ('C100', 161.4, 135.6, 90),
    ('C107', 170.6, 157.4, 90),
]
# F.Cu areas reserved for wide copper (x0, y0, x1, y1): NEAR parts do not go there
RESERVED = [(154.6, 159.0, 159.5, 162.2), (159.5, 159.0, 173.6, 160.7), (154.6, 162.2, 158.6, 168.0),
            (152.2, 155.5, 157.2, 158.2), (173.4, 128.4, 186.4, 131.8), (167.5, 156.4, 169.4, 159.0),
            (181.0, 166.3, 182.2, 169.0), (182.4, 170.8, 183.7, 172.0), (177.9, 169.2, 179.4, 171.6),
            (173.3, 168.9, 174.4, 171.9)] + [(143.4, y - 1.7, 154.2, y + 1.7) for y in FUSE_Y.values()]


def court(fp):
    r = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
    if r.GetWidth() <= 0:
        r = fp.GetBoundingBox(False)
    return (mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom()))


def hit(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def put(fp, x, y, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))


def place():
    board = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    moving = set(FIX) | {n[0] for n in NEAR}
    for ref, (x, y, rot) in FIX.items():
        put(fps[ref], x, y, rot)
    done = {r: court(fp) for r, fp in fps.items() if r not in moving and not fp.IsFlipped()}
    for fp in board.GetFootprints():        # locating pegs of the cell holders and other bare holes
        for k, p in enumerate(fp.Pads()):
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                x, y, r = mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetDrillSize().x) / 2 + 0.35
                done['hole %s %d' % (fp.GetReference(), k)] = (x - r, y - r, x + r, y + r)
    for ref in FIX:
        c = court(fps[ref])
        for o, oc in done.items():
            if hit(c, oc, -0.02):
                print('OVERLAP', ref, [round(v, 2) for v in c], o, [round(v, 2) for v in oc])
        done[ref] = c
    for ref, tx, ty, rot in NEAR:
        fp = fps[ref]
        best = None
        for ring in range(0, 61):
            d = ring * 0.25
            cand = [(tx, ty)] if ring == 0 else \
                [(tx + sx * d, ty + k * 0.25) for k in range(-ring, ring + 1) for sx in (-1, 1)] + \
                [(tx + k * 0.25, ty + sy * d) for k in range(-ring + 1, ring) for sy in (-1, 1)]
            cand.sort(key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
            for x, y in cand:
                for r in (rot, (rot + 90) % 360, (rot + 180) % 360, (rot + 270) % 360):
                    put(fp, x, y, r)
                    c = court(fp)
                    if c[0] < LIMIT[0] or c[1] < LIMIT[1] or c[2] > LIMIT[2] or c[3] > LIMIT[3]:
                        continue
                    if any(hit(c, oc, 0.1) for oc in done.values()) or any(hit(c, rr, 0.15) for rr in RESERVED):
                        continue
                    best = (x, y, r)
                    break
                if best:
                    break
            if best:
                break
        if not best:
            print('NO ROOM for', ref)
            continue
        put(fp, *best)
        done[ref] = court(fp)
        if abs(best[0] - tx) + abs(best[1] - ty) > 2.0:
            print('%s placed %.1f mm from its target at %.2f, %.2f rot %d' % (
                ref, ((best[0] - tx) ** 2 + (best[1] - ty) ** 2) ** 0.5, best[0], best[1], best[2]))
    board.Save(PCB)
    for ref in ('U101', 'U104', 'L100', 'L101', 'Q100', 'Q101', 'Q102', 'Q103', 'R115', 'C119', 'C122', 'C123',
                'C113', 'U107', 'L102', 'U108', 'L103', 'F100'):
        print(ref, ' '.join('%s:%s@%.2f,%.2f' % (p.GetNumber(), p.GetNetname().split('/')[-1][:9],
                                                 mm(p.GetPosition().x), mm(p.GetPosition().y))
                            for p in fps[ref].Pads() if p.GetNumber())[:520])


LOCAL = ('VSYS', 'CELL+', 'CELL-', '+12V_BOOST', '+12V_SENSE', 'SYS_DCIN', '+3V5', 'VBUS', '+5V')
PAIR = ('HS_USB_DP', 'HS_USB_DM')
# B.Cu corridors of the bars (other nets must leave them)
BARS = [(99.9, y - 1.9, 147.7, y + 1.9) for y in CELL_Y.values()] + [
    (143.8, 128.0, 147.7, 142.4), (143.8, 169.7, 147.7, 186.0), (150.5, 116.8, 155.5, 174.6),
    (179.2, 115.4, 186.6, 187.5), (174.3, 174.5, 176.7, 197.7), (143.0, 195.3, 176.7, 197.7)]


BRIDGE = (144.4, 195.1, 153.5, 197.7)       # SYS_DCIN crosses the USB pair here on F.Cu (all layers cleared)


def inside(p, r):
    return r[0] <= mm(p.x) <= r[2] and r[1] <= mm(p.y) <= r[3]


def crosses(t, r):
    a, e = t.GetStart(), t.GetEnd()
    n = max(1, int(mm(t.GetLength()) / 0.2))
    return any(inside(pcbnew.VECTOR2I(int(a.x + (e.x - a.x) * k / n), int(a.y + (e.y - a.y) * k / n)), r)
               for k in range(n + 1))


def rip():
    board = pcbnew.LoadBoard(PCB)
    kill = []
    for t in board.GetTracks():
        n = t.GetNetname()
        if n.endswith(PAIR):
            continue
        via = t.GetClass() == 'PCB_VIA'
        if n.startswith('/Power/') or n in LOCAL:
            kill.append(t)
        elif via:
            # ground stitching beside the USB pair (x 147.4 .. 150.8) stays
            if inside(t.GetPosition(), BOX) and not (n == 'GND' and 147.4 <= mm(t.GetPosition().x) <= 150.8):
                kill.append(t)
        elif crosses(t, BOX) and not t.IsLocked():
            kill.append(t)
        elif t.GetLayer() == pcbnew.B_Cu and not t.IsLocked() and any(crosses(t, r) for r in BARS):
            kill.append(t)
        elif not t.IsLocked() and crosses(t, BRIDGE):
            kill.append(t)
    # through vias of other nets inside a bar corridor go too, with the segments that end on them
    dead = {id(t) for t in kill}
    spots = []
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA' and id(t) not in dead and not t.GetNetname().endswith(PAIR) \
                and not (t.GetNetname() == 'GND' and 147.4 <= mm(t.GetPosition().x) <= 150.8) \
                and any(inside(t.GetPosition(), (r[0] - 0.6, r[1] - 0.6, r[2] + 0.6, r[3] + 0.6)) for r in BARS):
            kill.append(t)
            spots.append((t.GetPosition().x, t.GetPosition().y, t.GetNetname()))
    dead = {id(t) for t in kill}
    for t in board.GetTracks():
        if t.GetClass() != 'PCB_VIA' and id(t) not in dead and not t.IsLocked():
            for x, y, n in spots:
                if t.GetNetname() == n and ((t.GetStart().x, t.GetStart().y) == (x, y)
                                            or (t.GetEnd().x, t.GetEnd().y) == (x, y)):
                    kill.append(t)
                    break
    print('tracks and vias removed:', len(kill), 'of', len(board.GetTracks()))
    for t in kill:
        board.Remove(t)
    board.Save(PCB)


def copper():
    board = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
    count = [0, 0]

    def pad(ref, num):
        q = [p for p in fps[ref].Pads() if p.GetNumber() == num][0].GetPosition()
        return (mm(q.x), mm(q.y))

    def trk(net, pts, w, layer=FCU):
        n = board.FindNet(net)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(F(x0), F(y0)))
            t.SetEnd(pcbnew.VECTOR2I(F(x1), F(y1)))
            t.SetWidth(F(w))
            t.SetLayer(layer)
            t.SetNet(n)
            t.SetLocked(True)
            board.Add(t)
            count[0] += 1

    def via(net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
        v.SetWidth(pcbnew.F_Cu, F(d))
        v.SetDrill(F(drill))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(board.FindNet(net))
        v.SetLocked(True)
        board.Add(v)
        count[1] += 1

    # stitching vias beside the USB pair that picked up another net from a pad they touched
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.IsLocked() and 147.4 <= mm(t.GetPosition().x) <= 150.8 \
                and BOX[1] <= mm(t.GetPosition().y) <= BOX[3] and t.GetNetname() != 'GND':
            print('stitching via back to GND at %.2f, %.2f (was %s)' % (
                mm(t.GetPosition().x), mm(t.GetPosition().y), t.GetNetname()))
            t.SetNet(board.FindNet('GND'))
    # ---- cells: one 3.5 mm bar per cell on B.Cu from the + contact to its fuse, 6 vias up to the fuse pad
    for k, fuse in ((1, 'F100'), (2, 'F101'), (3, 'F102'), (4, 'F103')):
        net, cy, fy = '/Power/CELL%d+' % k, CELL_Y[k], FUSE_Y[fuse]
        pts = [(101.75, cy), (145.4, cy)] + ([(145.4, fy)] if abs(fy - cy) > 0.01 else [])
        trk(net, pts, 3.5, BCU)
        p1, p2 = pad(fuse, '1'), pad(fuse, '2')
        for dy in (-1.0, 0.0, 1.0):
            for x in (143.9, 144.6):
                via(net, x, fy + dy)
            trk(net, [(143.9, fy + dy), (p1[0], fy + dy)], 0.8)
            for x in (152.5, 153.3):
                via('CELL+', x, fy + dy)
            trk('CELL+', [(p2[0], fy + dy), (153.3, fy + dy)], 0.8)
    # ---- CELL+ collector on B.Cu (4.6 mm), up to the charger BAT pins through 9 vias
    trk('CELL+', [(153.0, FUSE_Y['F103']), (153.0, FUSE_Y['F100'])], 4.6, BCU)
    for y in (156.3, 157.1, 157.9):
        for x in (152.8, 153.6, 154.4):
            via('CELL+', x, y)
        trk('CELL+', [(152.8, y), (156.2, y)], 0.8)
    trk('CELL+', [(156.2, 156.3), (156.2, 157.9)], 0.8)
    b13 = pad('U101', '13')
    trk('CELL+', [(156.2, b13[1] + 0.44), (b13[0] + 0.2, b13[1] + 0.44)], 0.6)
    # ---- CELL- bar on B.Cu through the four - contacts, protection FETs on top of it
    # 3 mm at the board-edge side of the contacts: F.Cu parts further in keep their ground vias
    trk('CELL-', [(185.0, CELL_Y[4]), (185.0, CELL_Y[1])], 2.8, BCU)
    s1, s3 = pad('Q100', '1'), pad('Q100', '3')
    for y in (s3[1], pad('Q100', '2')[1], s1[1]):
        trk('CELL-', [(s1[0], y), (185.3, y)], 0.5)
    trk('CELL-', [(185.3, s3[1] + 0.05), (185.3, s1[1] + 0.35)], 1.6)
    for y in (s3[1] + 0.05, s3[1] + 0.85, s3[1] + 1.65):
        for x in (185.0, 185.8):
            via('CELL-', x, y)
    trk('/Power/PROT_MID', [pad('Q101', '5'), pad('Q100', '5')], 2.4)
    g1, g3 = pad('Q101', '1'), pad('Q101', '3')
    for y in (g1[1], pad('Q101', '2')[1], g3[1]):
        trk('GND', [(g1[0], y), (174.5, y)], 0.5)
    trk('GND', [(174.5, g1[1]), (174.5, g3[1] + 0.05)], 1.4)
    for y in (g1[1] - 0.1, g1[1] + 0.7, g1[1] + 1.5):
        for x in (174.2, 173.5):
            via('GND', x, y)
    # ---- VSYS: SYS pins -> neck -> bus -> tongue to the boost inductor; thinner bus to the other converters
    s15, s16 = pad('U101', '15'), pad('U101', '16')
    xm = (s15[0] + s16[0]) / 2
    l1 = pad('L101', '1')
    trk('VSYS', [(xm, s15[1] + 0.15), (xm, 159.4)], 0.7)
    trk('VSYS', [(l1[0], 160.6), (158.0, 160.6)], 3.0)
    trk('VSYS', [(l1[0], 160.6), l1], 3.6)
    trk('VSYS', [(158.0, 159.85), (pad('L102', '1')[0], 159.85)], 1.5)
    q = pad('L100', '2')
    trk('VSYS', [q, (q[0], 159.85)], 1.4)
    for c in ('C113', 'C114'):
        q = pad(c, '1')
        trk('VSYS', [(q[0], 159.85), q], 1.0)
    for x, y in ((155.7, 163.2), (157.5, 163.2), (155.7, 165.2), (157.5, 165.2)):
        via('VSYS', x, y)                       # into the VSYS pour on In2
    # ---- charger switch node
    q = pad('L100', '1')
    trk('/Power/BQ_SW', [(pad('U101', '19')[0] + 0.15, (pad('U101', '19')[1] + pad('U101', '20')[1]) / 2),
                         (q[0], q[1] - 0.1)], 0.7)
    # ---- 12 V boost: switch node, output, load switch, shunt, ideal diode
    sw, vo = pad('U104', '7'), pad('U104', '8')
    q = pad('L101', '2')
    trk('/Power/B12_SW', [(sw[0] - 1.7, sw[1]), (sw[0] - 2.7, sw[1])], 0.45)
    trk('/Power/B12_SW', [(sw[0] - 2.7, sw[1]), (sw[0] - 3.7, sw[1] + 1.0), (sw[0] - 3.7, q[1] - 1.5)], 1.4)
    c1 = pad('C119', '1')
    qs = [pad('Q102', n) for n in '123']
    trk('/Power/B12_VOUT', [(vo[0] + 1.7, vo[1]), (vo[0] + 2.6, vo[1])], 0.45)
    trk('/Power/B12_VOUT', [(vo[0] + 2.6, vo[1] - 0.15), (c1[0] - 0.4, c1[1] + 0.08), (qs[0][0], c1[1] + 0.08)], 1.1)
    trk('/Power/B12_VOUT', [(qs[0][0], c1[1] + 0.08), (qs[2][0], qs[2][1] - 0.08)], 0.5)
    d = pad('Q102', '5')
    b2, b3 = pad('C124', '1'), pad('C123', '1')
    r1, r2 = pad('R115', '1'), pad('R115', '2')
    trk('+12V_BOOST', [(d[0] + 0.4, d[1] - 1.0), (b2[0], b2[1] + 0.07)], 1.0)
    trk('+12V_BOOST', [(d[0] + 0.8, d[1] + 0.7), (r1[0] - 1.36, d[1] + 2.5), (r1[0] - 1.36, r1[1] - 0.5), r1, b3], 1.0)
    ss = [pad('Q103', n) for n in '123']
    trk('+12V_SENSE', [(r2[0], r2[1] + 0.4), (ss[0][0], ss[1][1] - 0.33)], 1.0)
    trk('+12V_SENSE', [(ss[0][0], ss[1][1] - 0.33), (ss[0][0], ss[0][1])], 0.5)
    dd = pad('Q103', '5')
    for y in (dd[1] - 1.1, dd[1] - 0.35, dd[1] + 0.4, dd[1] + 1.15):
        via('SYS_DCIN', 173.9, y)
        trk('SYS_DCIN', [(173.9, y), (dd[0] - 1.0, y)], 0.6)
    j36, j38 = pad('J1', '36'), pad('J1', '38')
    trk('SYS_DCIN', [(173.9, dd[1] - 1.1), (173.9, dd[1] + 1.15)], 0.6, BCU)
    trk('SYS_DCIN', [(173.9, dd[1]), (175.5, dd[1] + 2.6), (175.5, 196.4), (152.3, 196.4)], 2.0, BCU)
    # the USB pair runs on B.Cu at x 149: cross it on F.Cu (In1 ground below), 4 vias each side
    trk('SYS_DCIN', [(152.3, 196.4), (145.6, 196.4)], 2.0)
    for y in (195.85, 196.95):
        for x in (151.9, 152.7, 145.2, 146.0):
            via('SYS_DCIN', x, y)
    for j in (j36, j38):
        trk('SYS_DCIN', [(145.6, 196.4), (j[0], j[1] - 0.8)], 0.8, BCU)
    # ---- 5 V boost switch node
    a, e = pad('L102', '2'), pad('U107', '2')
    trk('/Power/B5_SW', [(a[0] + 0.2, a[1]), (e[0] - 1.05, e[1])], 0.8)
    trk('/Power/B5_SW', [(e[0] - 1.05, e[1]), (e[0] - 0.5, e[1])], 0.25)
    print('wide copper added: %d track segments, %d vias' % tuple(count))
    board.Save(PCB)


def lock():
    """After relock.py (which frees everything that is not in the reference board): lock the wide copper again."""
    board = pcbnew.LoadBoard(PCB)
    n = 0
    for t in board.GetTracks():
        name = t.GetNetname()
        if not (name.startswith('/Power/') or name in LOCAL or name == 'GND'):
            continue
        if t.GetClass() == 'PCB_VIA':
            wide = mm(t.GetWidth(pcbnew.F_Cu)) >= 0.59 and name != 'GND'
        else:
            wide = mm(t.GetWidth()) >= 0.45 and name != 'GND'
        if wide and not t.IsLocked():
            t.SetLocked(True)
            n += 1
    print('wide power copper locked:', n)
    board.Save(PCB)


if __name__ == '__main__':
    {'place': place, 'rip': rip, 'copper': copper, 'lock': lock}[sys.argv[1]]()
    sys.stdout.flush()
    os._exit(0)
