"""Initial placement of the r3.0 main board (run with KiCad's bundled python).

- Outline, mounting holes and every mechanically constrained part follow the enclosure model
  (case/meshtastic-concept/enclosure_concept.py; board frame x right, y up, y = 0 at the Bubblegum-96
  USB/HDMI edge). The board is L-shaped: 85 mm wide over the Bubblegum-96, 90.5 mm over the cells.
- The MMDVM block (two ADF7021, STM32, LEDs) is copied from the proven r1.3 layout including tracks and
  vias; r1.3 nets are mapped pad by pad onto the new nets and dangling stubs are removed.
- All other parts are packed by functional block into zones, avoiding holes and placed parts.
  Nothing outside the MMDVM block is routed: this is a starting point for manual layout.

KiCad coordinates: X = X0 + x, Y = Y0 - y.
"""
import json
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..'))
R13 = os.path.normpath(os.path.join(HERE, '..', '..', 'r1.3', 'mmdvm_hs_dual_hat.kicad_pcb'))
FPDIR = os.environ.get('KICAD_FOOTPRINT_DIR', r'C:/Program Files/KiCad/10.0/share/kicad/footprints')
KCLI = os.environ.get('KICAD_CLI', r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
LIBS = {'MMDVM': os.path.normpath(os.path.join(HERE, '..', '..', '..', 'libraries', 'mmdvm_hs_dual_hat.pretty')),
        'MMDVM_r30': os.path.join(PRJ, 'MMDVM_r30.pretty')}
X0, Y0 = 100.0, 250.0
# outline (model coordinates), counter-clockwise
OUTLINE = [(0.0, -1.0), (85.0, -1.0), (85.0, 54.0), (88.5, 54.0), (88.5, 166.0), (-2.0, 166.0), (-2.0, 54.0),
           (0.0, 54.0)]
EDGE_Y = 166.0                      # +Y edge = left side face when standing (13 mm added for the RJ45)
CELL_X, CELL_Y0, CELL_PITCH = 43.25, 55.0 + 10.875, 21.8
HOLES = [(4.0, 18.5), (4.0, 50.0), (81.0, 18.5), (81.0, 50.0), (4.0, 150.0), (84.0, 162.0)]
_KEEP = []

# ref: (x, y, rotation, side); edge parts are snapped to EDGE_Y afterwards
FIXED = {
    'J1': (29.0, 50.0, 270, 'B'),           # 96Boards LS (mirrored-number footprint), centre line y = 50
    'BT100': (CELL_X, CELL_Y0, 0, 'B'), 'BT101': (CELL_X, CELL_Y0 + CELL_PITCH, 0, 'B'),
    'BT102': (CELL_X, CELL_Y0 + 2 * CELL_PITCH, 0, 'B'), 'BT103': (CELL_X, CELL_Y0 + 3 * CELL_PITCH, 0, 'B'),
    'J2': (9.0, 159.0, 0, 'F'), 'J100': (23.7, 159.0, 0, 'F'), 'SW100': (33.7, 159.0, 0, 'F'),
    'SW50': (42.1, 159.0, 0, 'F'), 'SW101': (53.0, 159.0, 0, 'F'), 'D51': (60.8, 159.0, 0, 'F'),
    'J60': (71.3, 150.0, 0, 'F'),           # RJ45, courtyard centred on this x (see below)
    'TP1': (49.5, 11.0, 0, 'B'),            # r1.3 SWD test point: moved off the HS connector pads
    'U60': (54.5, 150.5, 270, 'F'),         # LAN7500 right behind the RJ45, TR0..TR3 pins (43-56) facing it
    'Y3': (59.6, 157.6, 0, 'F'),            # 25 MHz crystal near the XI/XO pins (5/6)
    'J10': (32.75, 15.45, 0, 'B'),          # 96Boards HS connector, position from the mezzanine template
    'J44': (0.0, 100.0, 0, 'F'),            # front-panel cable, opening towards the x = -2 edge
    'J5': (44.0, 6.0, 0, 'F'),              # TJC display
    'P5': (74.0, 34.5, 90, 'F'), 'P7': (75.0, 41.5, 90, 'F'),   # THT headers away from the Bubblegum USB-A
    'U40': (30.8, 106.5, 0, 'F'),           # RAK4630 in the gap between the cell-holder locating holes
    'J40': (46.2, 102.3, 0, 'F'),           # LoRa U.FL right next to RAK pad 37 (42.2, 102.3)
    'J41': (15.8, 110.7, 180, 'F'),         # BLE U.FL, centre pin facing RAK pad 15 (19.4, 110.7): 1.5 mm feed
    # GPS antenna connector and bias tee right beside MAX-M10S RF_IN (pin 11): 5 mm feed on F.Cu only
    'J50': (39.9, 123.5, 270, 'F'), 'L50': (38.8, 128.93, 270, 'F'), 'C84': (40.35, 129.7, 0, 'F'),
    'J3': (79.0, 64.0, 0, 'F'),             # fan cable towards the top plenum
}
R13_TURN = {'P1': 180}              # r1.3 parts turned in place: U.FL centre pin towards its filter (L2)
# +Y edge parts: (rotation, 'pad' = edge-side SMD pads end `val` from the edge | 'court' = courtyard, val)
EDGE_PARTS = {'J100': (180, 'court', 0.6), 'SW100': (180, 'pad', -0.35), 'SW50': (180, 'pad', -0.35),
              'D51': (90, 'court', -1.0), 'J60': (180, 'court', 1.0), 'SW101': (180, 'court', -0.1)}
CONSOLE_TIP = 1.6                   # console pin tips beyond the board edge (stay inside the enclosure wall)
ZONES = {   # model x0, y0, x1, y1 (filled bottom-up, left to right)
    'Host interface': (5.0, 54.0, 87.0, 76.0),
    'Power': (44.0, 77.0, 87.0, 145.0),
    'Meshtastic': (5.0, 77.0, 43.5, 120.0),
    'GPS': (5.0, 120.0, 42.0, 143.5),
    'Ethernet': (22.0, 144.5, 60.5, 161.0),
    'MMDVM IO': (56.0, 37.0, 76.0, 46.0),
}
PREFER = {'J42': 'Meshtastic',
          'J43': 'Meshtastic', 'J50': 'GPS', 'U35': 'GPS', 'Y2': 'GPS'}
# power-zone grid order (3 per row): each converter next to its inductor, FETs next to what they switch
POWER_ORDER = ['U104', 'L101', 'Q102', 'U101', 'L100', 'U100', 'U107', 'L102', 'U108', 'L103', 'U109', 'U110',
               'Q100', 'Q101', 'U102', 'U103', 'U105', 'U106', 'Q103', 'U111']
R13_ORIGIN = (90.2, 82.5)
R13_DX, R13_DY = 10.0, -53.0


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(X0 + x), mm(Y0 - y))


def model(q):
    return pcbnew.ToMM(q.x) - X0, Y0 - pcbnew.ToMM(q.y)


def netlist():
    path = os.path.join(PRJ, 'n_main.net')
    subprocess.run([KCLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', path,
                    os.path.join(PRJ, 'mmdvm_mesh.kicad_sch')], capture_output=True)
    s = open(path, encoding='utf-8').read()
    os.remove(path)
    comps = {}
    for blk in re.split(r'\n\t\t\(comp\n', s[s.index('(components'):s.index('(libparts')])[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        comps[ref] = dict(
            val=re.search(r'\(value "([^"]*)"\)', blk).group(1),
            fp=re.search(r'\(footprint "([^"]*)"\)', blk).group(1),
            sheet=re.search(r'\(sheetpath\s*\(names "([^"]*)"\)', blk).group(1).strip('/'),
            path=re.search(r'\(sheetpath\s*\(names "[^"]*"\)\s*\(tstamps "([^"]*)"\)', blk).group(1)
            + re.findall(r'\(tstamps "([^"]+)"\)', blk)[-1],
            fields={k: v for k, v in re.findall(r'\(field\s*\(name "([^"]+)"\)\s*(?:"((?:[^"\\]|\\.)*)")?\s*\)', blk)},
            dnp='"dnp"' in blk)
    pins = {}
    for blk in re.split(r'\n\t\t\(net\n', s[s.index('(nets'):])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        for r_, p_ in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            pins[(r_, p_)] = name
    return comps, pins


def load_fp(fpid):
    lib, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(LIBS.get(lib) or os.path.join(FPDIR, lib + '.pretty'), name)
    _KEEP.append(fp)
    return fp


def court(fp):
    """Courtyard bbox in model coordinates (x0, y0, x1, y1)."""
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    try:
        r = fp.GetCourtyard(layer).BBox()
        if r.GetWidth() <= 0:
            raise ValueError
    except Exception:  # noqa: BLE001
        r = fp.GetBoundingBox(False)
    x0, y1 = model(pcbnew.VECTOR2I(r.GetX(), r.GetY()))
    x1, y0 = model(pcbnew.VECTOR2I(r.GetX() + r.GetWidth(), r.GetY() + r.GetHeight()))
    return x0, y0, x1, y1


def cluster_order(refs, pins):
    """Order parts so that passives follow the IC they share signal nets with (keeps clusters together)."""
    members = {}
    for (r_, p_), n in pins.items():
        members.setdefault(n, set()).add(r_)
    sig = {n: m for n, m in members.items() if len(m) <= 6 and not n.startswith('unconnected')}
    adj = {r_: set() for r_ in refs}
    for m in sig.values():
        for a in m:
            if a in adj:
                adj[a] |= {b for b in m if b in adj and b != a}
    key = lambda r_: (re.sub(r'\d', '', r_), int(re.sub(r'\D', '', r_) or 0))
    big = sorted([r_ for r_ in refs if r_.startswith(('U', 'Q', 'J', 'SW'))], key=key)
    out, seen = [], set()

    def visit(r_, depth):
        if r_ in seen:
            return
        seen.add(r_)
        out.append(r_)
        if depth < 2:
            for nb in sorted(adj[r_], key=key):
                if not nb.startswith(('U', 'Q', 'J', 'SW')):
                    visit(nb, depth + 1)
    for r_ in big:
        visit(r_, 0)
    for r_ in sorted(refs, key=key):
        visit(r_, 0)
    return out


def write_rules():
    """Design rules live in the project file: set them explicitly (4-layer, 0.1/0.15 mm class)."""
    pro = os.path.join(PRJ, 'mmdvm_mesh.kicad_pro')
    d = json.load(open(pro, encoding='utf-8')) if os.path.exists(pro) else {}
    ds = d.setdefault('board', {}).setdefault('design_settings', {})
    rules = ds.setdefault('rules', {})
    rules.update({'min_clearance': 0.1, 'min_track_width': 0.15, 'min_via_diameter': 0.45,
                  'min_through_hole_diameter': 0.2, 'min_via_annular_width': 0.1, 'min_copper_edge_clearance': 0.3,
                  'min_hole_clearance': 0.1, 'min_hole_to_hole': 0.25, 'solder_mask_to_copper_clearance': 0.0,
                  'min_silk_clearance': 0.0})
    ds['allow_soldermask_bridges_in_footprints'] = True
    ns = d.setdefault('net_settings', {})
    classes = ns.setdefault('classes', [{'name': 'Default'}])
    for c in classes:
        if c.get('name') == 'Default':
            c.update({'clearance': 0.1, 'track_width': 0.2, 'via_diameter': 0.5, 'via_drill': 0.25})
    classes[:] = [c for c in classes if c.get('name') != 'Power']
    classes.append({'name': 'Power', 'clearance': 0.1, 'track_width': 0.4, 'via_diameter': 0.6, 'via_drill': 0.3,
                    'bus_width': 12, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25, 'diff_pair_width': 0.2,
                    'line_style': 0, 'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'wire_width': 6,
                    'pcb_color': 'rgba(0, 0, 0, 0.000)', 'schematic_color': 'rgba(0, 0, 0, 0.000)'})
    ns['netclass_patterns'] = [{'netclass': 'Power', 'pattern': pat} for pat in (
        'VSYS', 'VBUS', 'CELL+', 'CELL-', '+5V', '+3V5', '+12V_BOOST', '+12V_SENSE', 'SYS_DCIN', '/Power/CELL*',
        '/Power/B12_SW', '/Power/B12_VOUT', '/Power/BQ_SW', '/Power/BQ_PMID', '/Power/B5_SW', '/Power/BB_L*',
        '/Power/PROT_MID', 'MESH_VBAT_NRF', '+3V3_ETH', '+1V2_ETH', '/Ethernet/ETH_SW*')]
    d.setdefault('meta', {'filename': 'mmdvm_mesh.kicad_pro', 'version': 3})
    json.dump(d, open(pro, 'w', encoding='utf-8'), indent=2)


def main():
    out = os.path.join(PRJ, 'mmdvm_mesh.kicad_pcb')
    if os.path.exists(out) and '--force' not in sys.argv:
        old = pcbnew.LoadBoard(out)
        loose = sum(1 for t in old.GetTracks() if not t.IsLocked())
        if loose > 200:
            raise SystemExit('%s is routed (%d tracks beyond the r1.3 block). Regenerating throws that away: '
                             'the wide power copper, VBUS, differential pairs and hand edits were made on the '
                             'routed board. Run with --force to do it anyway.' % (out, loose))
    comps, pins = netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    nets = {}
    for n in sorted(set(pins.values())):
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        nets[n] = ni
    for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    placed = {}

    def add(ref, x=None, y=None, rot=0, side='F', pos=None):
        c = comps[ref]
        fp = load_fp(c['fp'])
        fp.SetParent(board)
        fp.SetReference(ref)
        fp.SetValue(c['val'])
        fp.SetFPIDAsString(c['fp'])
        fp.SetPath(pcbnew.KIID_PATH(c['path']))
        fp.SetSheetname(c['sheet'])
        for k, v in c['fields'].items():
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
            f.SetText(v); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
            f.SetOrdinal(fp.GetNextFieldOrdinal())
            fp.Add(f)
        if c['dnp']:
            fp.SetDNP(True)
        p_ = pos if pos is not None else P(x, y)
        fp.SetPosition(p_)
        if side == 'B':
            fp.Flip(p_, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for pad in fp.Pads():
            n = pins.get((ref, pad.GetNumber()))
            if n in nets:
                pad.SetNet(nets[n])
        placed[ref] = fp
        return fp

    for i, (hx, hy) in enumerate(HOLES):
        h = load_fp('MountingHole:MountingHole_2.7mm_M2.5_Pad_Via')
        h.SetParent(board); h.SetReference('H%d' % (i + 1)); h.SetPosition(P(hx, hy)); h.SetBoardOnly(True)
        h.SetExcludedFromBOM(True); h.SetExcludedFromPosFiles(True)
        board.Add(h)
        for pad in h.Pads():
            pad.SetNet(nets['GND'])
    # ---- MMDVM block from r1.3
    b13 = pcbnew.LoadBoard(R13)
    netmap, conflict = {}, set()
    for fp13 in b13.GetFootprints():
        ref = fp13.GetReference()
        if ref not in comps or not comps[ref]['sheet'].startswith('MMDVM') or ref in FIXED:
            continue
        q = fp13.GetPosition()
        u, v = pcbnew.ToMM(q.x) - R13_ORIGIN[0], pcbnew.ToMM(q.y) - R13_ORIGIN[1]
        add(ref, pos=pcbnew.VECTOR2I(mm(X0 + R13_DX + u), mm(Y0 + R13_DY + v)), rot=fp13.GetOrientationDegrees() + R13_TURN.get(ref, 0),
            side='B' if fp13.IsFlipped() else 'F')
        for pad13 in fp13.Pads():
            n13, nn = pad13.GetNetname(), pins.get((ref, pad13.GetNumber()))
            if n13 and nn:
                if netmap.get(n13, nn) != nn:
                    conflict.add(n13)
                netmap[n13] = nn
    off = pcbnew.VECTOR2I(mm(X0 + R13_DX - R13_ORIGIN[0]), mm(Y0 + R13_DY - R13_ORIGIN[1]))
    for t in b13.GetTracks():
        n13 = t.GetNetname()
        if n13 not in netmap or n13 in conflict or t.GetClass() == 'PCB_ARC':
            continue
        if t.GetClass() == 'PCB_VIA':
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(t.GetPosition() + off); v.SetWidth(t.GetWidth(pcbnew.F_Cu)); v.SetDrill(t.GetDrill())
        else:
            v = pcbnew.PCB_TRACK(board)
            v.SetStart(t.GetStart() + off); v.SetEnd(t.GetEnd() + off); v.SetWidth(t.GetWidth())
            v.SetLayer(t.GetLayer())
        v.SetNet(nets[netmap[n13]])
        board.Add(v)
    # R32 (1 k in the TJC TX line) sits on the old NXT header pin 2, so the proven r1.3 DISP_RXD track from
    # the STM32 ends on its pad
    p4 = [f for f in b13.GetFootprints() if f.GetReference() == 'P4']
    if p4 and 'R32' in comps:
        q = [p_ for p_ in p4[0].Pads() if p_.GetNumber() == '2'][0].GetPosition() + off
        r32 = add('R32', pos=q)
        pad = [p_ for p_ in r32.Pads() if pins.get(('R32', p_.GetNumber())) == 'DISP_RXD'][0]
        r32.Move(q - pad.GetPosition())
    print('r1.3 block:', len(placed), 'footprints; net conflicts', sorted(conflict))
    # ---- fixed parts
    for ref, (x, y, rot, side) in FIXED.items():
        if ref in comps and ref not in placed:
            add(ref, x, y, rot, side)
    j1 = placed['J1']
    pad = {p.GetNumber(): model(p.GetPosition()) for p in j1.Pads()}
    print('J1 pads 1/2/39 (model):', [tuple(round(v, 2) for v in pad[n]) for n in ('1', '2', '39')],
          '-> rows must be y 49 (odd) / 51 (even) offset outwards, x 10 .. 48')
    # +Y edge parts. Rotation 180 turns a footprint's +y (actuator / mouth side in the KiCad libraries) towards
    # the board edge. Switches: the pads nearest the edge stop 0.35 mm inside it (copper-to-edge rule), which
    # leaves the PCM12 lever about 1 mm and the SKRT plunger about 0.2 mm beyond the edge.
    edge_info = {}
    for ref, (rot, mode, val) in EDGE_PARTS.items():
        fp = placed[ref]
        fp.SetOrientationDegrees(rot)
        if mode == 'pad':
            top = max(Y0 - pcbnew.ToMM(p.GetBoundingBox().GetY()) for p in fp.Pads()
                      if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)
        else:
            top = court(fp)[3]
        fp.Move(P(0, EDGE_Y + val - top) - P(0, 0))
        fab = fp.GetBoundingBox(False)
        edge_info[ref] = round(Y0 - pcbnew.ToMM(fab.GetY()) - EDGE_Y, 2)
    for ref in ('J60', 'SW101'):                    # centre the body (footprint origin is pin 1)
        if ref in placed:
            c = court(placed[ref])
            placed[ref].Move(P(FIXED[ref][0] - (c[0] + c[2]) / 2, 0) - P(0, 0))
    if 'J10' in placed:
        pad = {p.GetNumber(): model(p.GetPosition()) for p in placed['J10'].Pads()}
        print('J10 pads 1/2/51 (model):', [tuple(round(v, 2) for v in pad[n]) for n in ('1', '2', '51')],
              '-> template: (21.15, 13.25) (21.15, 17.65) (41.15, 13.25)')
    # 49.9 ohm terminations of the Ethernet pairs: on the bottom side right at the RJ45 signal pins (through
    # hole), so the branch from the line to the resistor is about 1 mm. Rear-row pins: resistor towards the
    # board centre, front-row pins: towards the jack body.
    if 'J60' in placed:
        jp = {p_.GetNumber(): model(p_.GetPosition()) for p_ in placed['J60'].Pads()}
        ymid = (jp['2'][1] + jp['3'][1]) / 2
        for ref, pin in (('R85', '2'), ('R86', '3'), ('R87', '4'), ('R88', '5'), ('R96', '6'), ('R97', '7'),
                         ('R98', '8'), ('R99', '9')):
            if ref not in comps:
                continue
            px, py = jp[pin]
            sgn = 1.0 if py > ymid else -1.0
            r_ = add(ref, px, py + sgn * 1.75, 90, 'B')
            net = pins[('J60', pin)]
            near = min(r_.Pads(), key=lambda q_: abs(model(q_.GetPosition())[1] - py))
            if pins.get((ref, near.GetNumber())) != net:
                r_.SetOrientationDegrees(270)
    j2 = placed['J2']                               # console header, pins towards the edge
    best = None
    for rot in (0, 90, 180, 270):
        j2.SetOrientationDegrees(rot)
        ys = [model(p.GetPosition())[1] for p in j2.Pads()]
        x0, y0, x1, y1 = court(j2)
        if max(ys) - min(ys) < 0.1 and (best is None or y1 - ys[0] > best[0]):
            best = (y1 - ys[0], rot)
    j2.SetOrientationDegrees(best[1])
    mx = sum(model(p.GetPosition())[0] for p in j2.Pads()) / len(j2.Pads())
    tip = Y0 - pcbnew.ToMM(j2.GetBoundingBox(False).GetY())          # pin tips
    j2.Move(P(FIXED['J2'][0] - mx, EDGE_Y + CONSOLE_TIP - tip) - P(0, 0))
    edge_info['J2'] = CONSOLE_TIP
    print('edge parts, outermost point beyond the board edge (mm):', edge_info)
    j44 = placed['J44']                             # opening towards x = -2
    best = None
    for rot in (0, 90, 180, 270):
        j44.SetOrientationDegrees(rot)
        x0, y0, x1, y1 = court(j44)
        cx = sum(model(p.GetPosition())[0] for p in j44.Pads() if p.GetNumber() != 'MP') / 6
        if best is None or (cx - x0) > best[0]:
            best = (cx - x0, rot)
    j44.SetOrientationDegrees(best[1])
    x0, y0, x1, y1 = court(j44)
    j44.Move(P(-2.0 - x0, 0) - P(0, 0))
    # ---- keep-outs for packing: holes through the board, and every placed part on the top side
    keep = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_NPTH, pcbnew.PAD_ATTRIB_PTH):
                x, y = model(p.GetPosition())
                r = pcbnew.ToMM(max(p.GetDrillSize().x, p.GetSize(pcbnew.F_Cu).x)) / 2 + 0.6
                keep.append((x - r, y - r, x + r, y + r))
        if not fp.IsFlipped():
            keep.append(court(fp))

    # corridor for the four Ethernet pairs between U60 and the RJ45 pins (pair_route.py lays them before the
    # autorouter runs): no terminations or decoupling capacitors in front of the TR pins or above the jack
    keep += [(59.1, 143.9, 62.0, 156.6), (59.1, 139.5, 80.5, 144.0)]
    if 'U60' in placed:               # ring around the 56-QFN: room for the pins to fan out with vias
        c = court(placed['U60'])
        keep.append((c[0] - 2.6, c[1] - 2.6, c[2] + 1.0, c[3] + 2.6))    # 2.6 mm: 1 mm left the bottom row boxed in

    def free(b):
        return all(b[2] <= k[0] or b[0] >= k[2] or b[3] <= k[1] or b[1] >= k[3] for k in keep)

    rest, zone_of = {}, {}
    for ref, c in comps.items():
        if ref in placed or ref.startswith('#') or not c['fp']:
            continue
        zone = PREFER.get(ref) or (c['sheet'] if c['sheet'] in ZONES else
                                   ('MMDVM IO' if c['sheet'].startswith('MMDVM') else 'Host interface'))
        rest.setdefault(zone, []).append(ref)
        zone_of[ref] = zone
    members, pins_of = {}, {}
    for (r_, p_), n in pins.items():
        members.setdefault(n, []).append((r_, p_))
        pins_of.setdefault(r_, []).append((p_, n))
    overflow = []

    def is_anchor(ref):
        return ref in POWER_ORDER or ref.startswith(('U', 'Q', 'J', 'SW', 'Y'))

    def shelf(ref, zone, margin):
        """First free slot scanning the zone bottom-up; `margin` reserves room around the part."""
        zx0, zy0, zx1, zy1 = ZONES[zone]
        fp = placed.get(ref) or add(ref, zx0, zy0)
        fp.SetOrientationDegrees(0)
        fp.SetPosition(P(zx0, zy0))
        x0, y0, x1, y1 = court(fp)
        w, h = x1 - x0 + 2 * margin, y1 - y0 + 2 * margin
        ox, oy = model(fp.GetPosition())
        dx, dy = ox - x0, oy - y0
        y = zy0
        while y + h <= zy1:
            x = zx0
            while x + w <= zx1:
                if free((x, y, x + w, y + h)):
                    fp.SetPosition(P(x + dx + margin, y + dy + margin))
                    keep.append(court(fp))
                    return True
                x += 0.5
            y += 0.5
        return False

    # 1) anchors (ICs, FETs, connectors, switches, crystals) with room around them for their passives
    def grid_place(refs, zone, cols):
        """Spread anchors over the zone, one per grid cell, so their passives fit around them."""
        zx0, zy0, zx1, zy1 = ZONES[zone]
        rows = -(-len(refs) // cols)
        cw, ch = (zx1 - zx0) / cols, (zy1 - zy0) / rows
        left = []
        cells = {ref: (zx0 + (i % cols + 0.5) * cw, zy0 + (i // cols + 0.5) * ch) for i, ref in enumerate(refs)}
        fps = {ref: add(ref, *cells[ref]) for ref in refs}

        def area(ref):
            c = court(fps[ref])
            return (c[2] - c[0]) * (c[3] - c[1])
        for ref in sorted(refs, key=area, reverse=True):          # big parts first
            ccx, ccy = cells[ref]
            fp = fps[ref]
            x0, y0, x1, y1 = court(fp)
            ok = False
            for r in [k * 0.5 for k in range(0, 14)]:
                for k in range(1 if r == 0 else 12):
                    a = 6.2832 * k / 12
                    dx, dy = r * math.cos(a), r * math.sin(a)
                    b = (x0 + dx - 0.6, y0 + dy - 0.6, x1 + dx + 0.6, y1 + dy + 0.6)
                    if b[0] >= zx0 and b[1] >= zy0 and b[2] <= zx1 and b[3] <= zy1 and free(b):
                        fp.SetPosition(P(ccx + dx, ccy + dy))
                        keep.append(court(fp))
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                left.append(ref)
        return left

    for zone, refs in rest.items():
        anchors = [r_ for r_ in cluster_order(refs, pins) if is_anchor(r_)]
        if zone == 'Power':
            anchors = grid_place([r_ for r_ in POWER_ORDER if r_ in anchors]
                                 + [r_ for r_ in anchors if r_ not in POWER_ORDER], zone, 3)
        for ref in anchors:
            m = 1.4
            if not (shelf(ref, zone, m) or shelf(ref, zone, 0.8) or shelf(ref, zone, 0.2)):
                overflow.append(ref)

    # 2) satellites: put each part next to the pad it connects to (most specific net first)
    def pad_xy(ref, num):
        for pad in placed[ref].Pads():
            if pad.GetNumber() == num:
                return model(pad.GetPosition())
        return None

    def bounds(zone):
        zx0, zy0, zx1, zy1 = ZONES[zone]
        if zone == 'MMDVM IO':
            return zx0, zy0, zx1, zy1
        return max(-1.4, zx0 - 8), max(54.4, zy0 - 8), min(87.9, zx1 + 8), min(EDGE_Y - 0.6, zy1 + 8)

    use = {}
    todo = [r_ for refs in rest.values() for r_ in refs if not is_anchor(r_)]
    far = []
    while todo:
        plan = []
        for ref in todo:
            opts = []
            for pin, net in pins_of.get(ref, []):
                if net == 'GND' or net.startswith('unconnected'):
                    continue
                tg = [t for t in members[net] if t[0] in placed and t[0] != ref and not placed[t[0]].IsFlipped()]
                if tg:
                    opts.append((len(members[net]), pin, net, tg))
            if opts:
                opts.sort(key=lambda o: o[0])
                plan.append((opts[0][0], ref, opts[0]))
        if not plan:
            break
        plan.sort(key=lambda q: (q[0], re.sub(r'\d', '', q[1]), int(re.sub(r'\D', '', q[1]) or 0)))
        for _n, ref, (cnt, pin, net, tg) in plan:
            tg.sort(key=lambda t: (0 if is_anchor(t[0]) else 1, use.get(t, 0), t))
            target = tg[0]
            txy = pad_xy(*target)
            fp = add(ref, 0, 0)
            bx0, by0, bx1, by1 = bounds(zone_of[ref])
            best = None
            for rot in (0, 90, 180, 270):
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(P(0, 0))
                c0 = court(fp)
                pxy = pad_xy(ref, pin)
                r = 0.0
                found = None
                while r < 30.0 and found is None and (best is None or r < best[0]):
                    for k in range(1 if r == 0 else max(8, int(r * 6))):
                        a = 6.2832 * k / max(8, int(r * 6))
                        fx = txy[0] + r * math.cos(a) - pxy[0]
                        fy = txy[1] + r * math.sin(a) - pxy[1]
                        b = (c0[0] + fx - 0.12, c0[1] + fy - 0.12, c0[2] + fx + 0.12, c0[3] + fy + 0.12)
                        if b[0] >= bx0 and b[1] >= by0 and b[2] <= bx1 and b[3] <= by1 and free(b):
                            found = (r, rot, fx, fy)
                            break
                    r += 0.3
                if found and (best is None or found[0] < best[0]):
                    best = found
            if best is None:
                if not shelf(ref, zone_of[ref], 0.15):
                    overflow.append(ref)
            else:
                fp.SetOrientationDegrees(best[1])
                fp.SetPosition(P(best[2], best[3]))
                keep.append(court(fp))
                use[target] = use.get(target, 0) + 1
                if best[0] > 6.0:
                    far.append((ref, round(best[0], 1)))
            todo.remove(ref)
    for ref in todo:                      # no connection to anything placed: just pack
        if not shelf(ref, zone_of[ref], 0.15):
            overflow.append(ref)
    print('placed', sum(len(v) for v in rest.values()), 'overflow', overflow, '| far from target (>6 mm):', far)
    # ---- remove dangling copies: a track end is anchored if it hits a pad, a via or another track
    pads_all = [p for fp in board.GetFootprints() for p in fp.Pads()]
    for t in list(board.GetTracks()):          # copies that leave the board or touch a pad of another net
        ends = [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
        kill = t.GetNetname() in ('RXD', 'TXD') or any(model(q)[1] < -0.55 for q in ends)
        if not kill:
            for p in pads_all:
                if p.GetNetname() != t.GetNetname() and (t.GetClass() == 'PCB_VIA' or p.IsOnLayer(t.GetLayer()))                         and t.HitTest(p.GetBoundingBox(), False, mm(0.12)):
                    kill = True
                    break
        if kill:
            board.Remove(t)
    for _ in range(40):
        tracks = list(board.GetTracks())
        segs = [t for t in tracks if t.GetClass() == 'PCB_TRACK']
        vias = [t for t in tracks if t.GetClass() == 'PCB_VIA']

        def anchored(q, layer, me):
            for p in pads_all:
                if p.IsOnLayer(layer) and p.HitTest(q):
                    return True
            for v in vias:
                if v is not me and v.HitTest(q):
                    return True
            for t in segs:
                if t is not me and t.GetLayer() == layer and t.HitTest(q):
                    return True
            return False
        gone = 0
        for t in segs:
            if t.GetLength() < mm(0.05) or not (anchored(t.GetStart(), t.GetLayer(), t)
                                                and anchored(t.GetEnd(), t.GetLayer(), t)):
                board.Remove(t)
                gone += 1
        segs = [t for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
        for v in vias:
            if v.GetNetname() == 'GND':
                continue
            q = v.GetPosition()
            n = sum(1 for t in segs if t.HitTest(q)) + sum(1 for p in pads_all if p.HitTest(q))
            if n < 2:
                board.Remove(v)
                gone += 1
        if not gone:
            break
    for t in board.GetTracks():
        t.SetLocked(True)                      # proven r1.3 routing: keep it out of the autorouter's hands
    print('r1.3 tracks kept:', len(board.GetTracks()))
    # ---- GND: inner plane In1, pours on F and B
    for layer in (pcbnew.In1_Cu, pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(nets['GND'])
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in OUTLINE:
            ol.Append(mm(X0 + x), mm(Y0 - y))
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    placed['U101'].SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)   # exposed pad + thermal vias: solid
    # ---- placement of the routed board (snapshot_placement.py): parts moved there keep their place
    snap = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'placement.json')
    if os.path.exists(snap):
        moved = 0
        for ref, (x, y, rot, side) in json.load(open(snap, encoding='utf-8')).items():
            fp = placed.get(ref)
            if fp is None or ('B' if fp.IsFlipped() else 'F') != side:
                continue
            q = pcbnew.VECTOR2I(mm(x), mm(y))
            if fp.GetPosition() != q or abs(fp.GetOrientationDegrees() - rot) > 0.01:
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(q)
                moved += 1
        print('placement.json applied:', moved, 'footprints moved')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(out)
    # the board reaches y = 251 mm, below an A4 landscape sheet (210 mm): use A3 so it sits inside the frame
    raw = open(out, 'rb').read()
    open(out, 'wb').write(raw.replace(b'(paper "A4")', b'(paper "A3")', 1))
    write_rules()
    print('saved', out, 'footprints', len(board.GetFootprints()))


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    os._exit(0)
