"""Place, route and pour the 26 x 20 mm front-panel board (run with KiCad's bundled python).

F side faces the enclosure front plate (switch actuator + LED); connectors and passives sit on B.
Board coordinates: origin = top-left of the board outline, mm, y down (top view from the front).
"""
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'front_panel'))
FPDIR = os.environ.get('KICAD_FOOTPRINT_DIR', r'C:/Program Files/KiCad/10.0/share/kicad/footprints')
KCLI = os.environ.get('KICAD_CLI', r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
X0, Y0 = 100.0, 100.0          # board origin on the page
W, H = 26.0, 20.0
_KEEP = []

# ref: (x, y, rotation, side)   side 'F' or 'B'
PLACE = {
    'SW1': (5.0, 9.75, 0, 'F'),      # footprint origin = pad 1; body centre (8.25, 12.0)
    'D1': (20.0, 9.0, 0, 'F'),
    'J2': (8.0, 3.2, 270, 'B'),      # pins at x 8.0 .. 15.62
    'J1': (19.0, 16.0, 180, 'B'),    # side entry, opening at the bottom edge
    'R1': (20.0, 6.0, 0, 'B'),
    'C1': (18.6, 3.2, 90, 'B'),
    'C2': (16.9, 6.0, 90, 'B'),
    'H1': (3.0, 3.0, 0, 'F'),
    'H2': (23.0, 3.0, 0, 'F'),
}


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(X0 + x), mm(Y0 + y))


def netlist():
    """ref -> (uuid path, value, footprint, fields), (ref, pin) -> net, from the schematic netlist."""
    net = os.path.join(OUT, 'n.net')
    subprocess.run([KCLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net,
                    os.path.join(OUT, 'front_panel.kicad_sch')], capture_output=True)
    s = open(net, encoding='utf-8').read()
    comps = {}
    for blk in re.split(r'\n\t\t\(comp\n', s[s.index('(components'):s.index('(libparts')])[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        val = re.search(r'\(value "([^"]*)"\)', blk).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk).group(1)
        ts = re.findall(r'\(tstamps "([^"]+)"\)', blk)[-1]
        fields = dict(re.findall(r'\(field\s*\(name "([^"]+)"\)\s*"([^"]*)"\)', blk))
        comps[ref] = (ts, val, fp, fields)
    pins = {}
    ns = s[s.index('(nets'):]
    for blk in re.split(r'\n\t\t\(net\n', ns)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        for r_, p_ in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            pins[(r_, p_)] = name
    return comps, pins


def build():
    comps, pins = netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_MinClearance = mm(0.15)
    nets = {}
    for n in sorted(set(pins.values())):
        if n.startswith('unconnected-'):
            continue
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        nets[n] = ni
    # outline with 1 mm corner radius
    r = 1.0
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for (a, b) in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    for (cx, cy, sa) in ((r, r, 180), (W - r, r, 270), (W - r, H - r, 0), (r, H - r, 90)):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetCenter(pt(cx, cy))
        import math
        a0 = math.radians(sa)
        s.SetStart(pt(cx + r * math.cos(a0), cy + r * math.sin(a0)))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    fps = {}
    for ref, (x, y, rot, side) in PLACE.items():
        ts, val, fpid, fields = comps[ref]
        lib, name = fpid.split(':')
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
        _KEEP.append(fp)
        fp.SetParent(board)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetFPIDAsString(fpid)
        fp.SetPath(pcbnew.KIID_PATH('/' + ts))
        for k, v in fields.items():
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
            f.SetText(v)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            f.SetOrdinal(fp.GetNextFieldOrdinal())
            fp.Add(f)
        fp.SetPosition(pt(x, y))
        if side == 'B':
            fp.Flip(pt(x, y), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for pad in fp.Pads():
            n = pins.get((ref, pad.GetNumber()))
            if n in nets:
                pad.SetNet(nets[n])
        fps[ref] = fp
    return board, fps, nets


def dump_pads(fps):
    for ref, fp in sorted(fps.items()):
        for pad in fp.Pads():
            p = pad.GetPosition()
            print(f'{ref}.{pad.GetNumber() or "-"} ({pcbnew.ToMM(p.x) - X0:6.2f},{pcbnew.ToMM(p.y) - Y0:6.2f}) '
                  f'{pad.GetNetname()} {"F" if pad.IsOnLayer(pcbnew.F_Cu) else ""}{"B" if pad.IsOnLayer(pcbnew.B_Cu) else ""}')


# (net, layer, width, [(x, y), ...])
TRACKS = [
    ('+3V3_MESH', 'B', 0.4, [(21.5, 14.0), (21.5, 5.2), (20.27, 3.97), (18.6, 3.97)]),
    ('+3V3_MESH', 'B', 0.4, [(18.6, 3.97), (18.0, 3.97), (18.0, 6.48), (16.9, 6.48)]),
    ('+3V3_MESH', 'B', 0.4, [(16.9, 6.48), (11.8, 6.48), (10.54, 5.22), (10.54, 3.2)]),
    ('SDA', 'B', 0.25, [(19.5, 14.0), (19.5, 12.6)]),
    ('SDA', 'F', 0.25, [(19.5, 12.6), (17.0, 10.1), (17.0, 5.2), (15.62, 3.82), (15.62, 3.2)]),
    ('SCL', 'B', 0.25, [(18.5, 14.0), (18.5, 12.6)]),
    ('SCL', 'F', 0.25, [(18.5, 12.6), (16.0, 10.1), (16.0, 6.2), (13.08, 3.28), (13.08, 3.2)]),
    ('BTN_N', 'B', 0.25, [(17.5, 14.0), (17.5, 12.6)]),
    ('BTN_N', 'F', 0.25, [(17.5, 12.6), (15.0, 10.1), (11.5, 10.1), (11.5, 9.75)]),
    ('LED_B', 'B', 0.25, [(16.5, 14.0), (16.5, 8.2), (18.7, 8.2), (19.49, 7.41), (19.49, 6.0)]),
    ('LED_A', 'B', 0.25, [(20.51, 6.0), (20.51, 7.2)]),
    ('LED_A', 'F', 0.25, [(20.51, 7.2), (20.94, 7.63), (20.94, 9.0)]),
    ('GND', 'B', 0.4, [(20.5, 14.0), (20.5, 12.4)]),
    ('BTN_N', 'B', 0.3, [(5.0, 9.75), (11.5, 9.75)]),      # the switch's two pin-1 pads
]
VIAS = [('SDA', 19.5, 12.6), ('SCL', 18.5, 12.6), ('BTN_N', 17.5, 12.6), ('LED_A', 20.51, 7.2),
        ('GND', 20.5, 12.4), ('GND', 2.0, 8.0), ('GND', 2.0, 17.5), ('GND', 12.5, 17.5), ('GND', 24.2, 9.5),
        ('GND', 8.5, 6.8), ('GND', 14.0, 15.5)]
TEXTS = [('B', 'r3.0 FRONT PANEL', 6.5, 18.6, 0.8),  # B text is mirrored: read from the back
         ('B', 'SDA SCL 3V3 GND', 11.8, 0.95, 0.8),
         ('B', 'J44', 23.6, 13.0, 0.8),
         ('F', 'MESH', 8.25, 17.6, 0.8)]


def route(board, nets):
    L = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}
    nets = dict(nets)
    for k in list(nets):
        if k.startswith('/'):
            nets[k[1:]] = nets[k]
    for (n, layer, w, pts) in TRACKS:
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*a)); t.SetEnd(pt(*b)); t.SetWidth(mm(w)); t.SetLayer(L[layer]); t.SetNet(nets[n])
            board.Add(t)
    for (n, x, y) in VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(x, y)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets[n])
        board.Add(v)
    for (side, txt, x, y, size) in TEXTS:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt); t.SetPosition(pt(x, y)); t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.15))
        t.SetLayer(pcbnew.B_SilkS if side == 'B' else pcbnew.F_SilkS)
        if side == 'B':
            t.SetMirrored(True)
        board.Add(t)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(nets['GND'])
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
            ol.Append(mm(X0 + x), mm(Y0 + y))
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


if __name__ == '__main__':
    board, fps, nets = build()
    route(board, nets)
    path = os.path.join(OUT, 'front_panel.kicad_pcb')
    board.Save(path)
    sys.stdout.flush()
    os._exit(0)
