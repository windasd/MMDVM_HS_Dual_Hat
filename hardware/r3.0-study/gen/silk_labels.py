"""Add the descriptive silkscreen: connector / LED / switch names, pin labels, board title.

Run after tidy_silk.py (run with KiCad's python). Labels from an earlier run (all board-level silk text) are
removed first. Each label is put at the free spot closest to its preferred position: clear of pads, holes,
other silk and the board edge. A label that finds no spot within its search radius is reported and skipped.

Usage: python silk_labels.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
SILK = (pcbnew.F_SilkS, pcbnew.B_SilkS)
if '--clear' in sys.argv:
    # Separate process: after removing board items the KiCad binding hands out broken proxies, so the labels of
    # an earlier run are removed here and nothing else is done.
    board = pcbnew.LoadBoard(PCB)
    old = [d for d in board.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() in SILK]
    for d in old:
        board.Remove(d)
    board.Save(PCB)
    print('old labels removed', len(old))
    sys.stdout.flush()
    os._exit(0)
import subprocess  # noqa: E402
subprocess.run([sys.executable, os.path.abspath(__file__), '--clear'], capture_output=True)
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
PAD_CL, SILK_CL, EDGE_CL = mm(0.15), mm(0.15), mm(0.5)
POLY = [(mm(M.X0 + x), mm(M.Y0 - y)) for x, y in M.OUTLINE]
SILK = (pcbnew.F_SilkS, pcbnew.B_SilkS)



def in_board(x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / float(y2 - y1):
            c = not c
    return c


def box(item):
    b = item.GetBoundingBox()
    return (b.GetX(), b.GetY(), b.GetX() + b.GetWidth(), b.GetY() + b.GetHeight())


fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
# the MMDVM status LEDs carry their function name instead of the reference (as on r1.3)
LEDS = (('D1', 'PWR'), ('D2', 'COS'), ('D3', 'PTT'), ('D4', 'D*'), ('D5', 'DMR'), ('D6', 'YSF'), ('D7', 'P25'),
        ('D8', 'NXD'))
for ref, _ in LEDS:
    fps[ref].Reference().SetVisible(False)
obst = [[], []]            # per side: (box, clearance)
for fp in fps.values():
    for p in fp.Pads():
        through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        for s, cu in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
            if through or p.IsOnLayer(cu):
                obst[s].append((box(p), PAD_CL))
    items = [g for g in fp.GraphicalItems()] + [f for f in fp.GetFields()]
    for g in items:
        if g.GetLayer() in SILK and (g.GetClass() == 'PCB_SHAPE' or g.IsVisible()):
            obst[0 if g.GetLayer() == pcbnew.F_SilkS else 1].append((box(g), SILK_CL))


def free(bx, s):
    if not all(in_board(x, y) for x in (bx[0] - EDGE_CL, bx[2] + EDGE_CL) for y in (bx[1] - EDGE_CL, bx[3] + EDGE_CL)):
        return False
    return not any(o[0] < bx[2] + cl and o[2] > bx[0] - cl and o[1] < bx[3] + cl and o[3] > bx[1] - cl
                   for o, cl in obst[s])


placed = skipped = 0


def label(text, x, y, size=1.0, ang=0, back=False, radius=6.0, bold=False, ymax=None):
    """Centre of the label as close as possible to (x, y) in board mm."""
    global placed, skipped
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetMirrored(back)
    t.SetTextAngleDegrees(ang)
    board.Add(t)
    s = 1 if back else 0
    step = 0.25
    n = int(radius / step)
    cands = sorted(((i * i + j * j, i * step, j * step) for i in range(-n, n + 1) for j in range(-n, n + 1)
                    if i * i + j * j <= n * n and (ymax is None or abs(j * step) <= ymax)))
    for _, dx, dy in cands:
        t.SetPosition(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
        b = box(t)
        c = ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
        t.SetPosition(pcbnew.VECTOR2I(2 * mm(x + dx) - c[0], 2 * mm(y + dy) - c[1]))
        b = box(t)
        if free(b, s):
            obst[s].append((b, SILK_CL))
            placed += 1
            return True
    board.Remove(t)
    skipped += 1
    print('no room:', text.replace('\n', ' / '))
    return False


def bb(ref):
    b = fps[ref].GetBoundingBox(False)
    return [pcbnew.ToMM(v) for v in (b.GetX(), b.GetY(), b.GetRight(), b.GetBottom())]


def pad(ref, num):
    p = [q for q in fps[ref].Pads() if q.GetNumber() == num][0].GetPosition()
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def beside(ref, text, where, size=1.0, gap=1.2, **kw):
    x0, y0, x1, y1 = bb(ref)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = len(text) * size * 0.45
    pos = {'N': (cx, y0 - gap), 'S': (cx, y1 + gap), 'W': (x0 - gap - w, cy), 'E': (x1 + gap + w, cy)}[where]
    return label(text, pos[0], pos[1], size, **kw)


# ---- MMDVM status LEDs (same names as r1.3)
for ref, name in LEDS:
    ok = beside(ref, name, 'E', 0.9, gap=0.5, bold=True, ymax=0.25)      # stays in the row of its LED
    if not ok:
        beside(ref, name, 'E', 0.8, gap=0.3, ymax=0.6)
beside('D0', 'SVC', 'W', 0.9, bold=True)
beside('D40', 'MESH', 'S', 0.8)
beside('D51', 'GPS', 'S', 0.8)
beside('D101', 'CHG', 'N', 0.8)

# ---- antennas
beside('P1', '433 TX', 'W', 1.2, bold=True)
beside('P2', '433 RX', 'W', 1.2, bold=True)
beside('J40', 'LoRa 920', 'S', 1.0, bold=True)
beside('J41', 'BLE', 'W', 1.0, bold=True)
beside('J50', 'GPS ANT', 'N', 1.0, bold=True)

# ---- +Y edge: console, charger, power button, GPS switch
beside('J2', 'CONSOLE 3V3', 'S', 1.0, gap=2.5, radius=10, bold=True)
x, y = pad('J2', '1')
label('GND', x - 2.6, y, 0.8)
beside('J100', 'USB-C CHARGE', 'S', 1.0, gap=3.0, bold=True)
beside('SW100', 'POWER', 'S', 1.0, gap=3.5, bold=True)
x_on, _ = pad('SW50', '1')        # lever towards pin 1 closes 1-2 (MESH_3V3_EN -> GPS_ON)
x_off, _ = pad('SW50', '3')
_, _, _, ys = bb('SW50')
label('ON', x_on + (1.2 if x_on > x_off else -1.2), ys + 1.0, 0.8)
label('OFF', x_off + (1.4 if x_off > x_on else -1.4), ys + 1.0, 0.8)
beside('SW50', 'GPS', 'S', 1.0, gap=2.4, radius=10, bold=True)
if 'SW101' in fps:                 # battery master switch: terminals 1/6 are the ON throws
    bx_on, _ = pad('SW101', '1')
    bx_off, _ = pad('SW101', '3')
    _, _, _, bys = bb('SW101')
    # short search radius: a label that lands next to the neighbouring GPS switch would mislead
    label('ON', bx_on + (1.0 if bx_on > bx_off else -1.0), bys + 0.9, 0.8, radius=3.5)
    label('OFF', bx_off + (1.2 if bx_off > bx_on else -1.2), bys + 0.9, 0.8, radius=3.5)
    label('BAT', (bx_on + bx_off) / 2, bys + 2.2, 0.8, radius=4.5, bold=True)
if 'J60' in fps:
    beside('J60', 'LAN', 'S', 1.0, radius=12, bold=True)

# ---- Meshtastic block
beside('J44', 'FRONT PANEL', 'E', 0.8, ang=0)
beside('J42', 'MESH SWD', 'N', 0.8)
beside('J43', 'MESH USB', 'N', 0.8)
beside('SW40', 'RESET', 'S', 0.8)
beside('SW41', 'USER', 'S', 0.8)
beside('TP50', 'SAFEBOOT', 'E', 0.8)

# ---- host side
beside('SW2', 'HOST RST', 'N', 0.8, radius=4) or beside('SW2', 'HOST RST', 'S', 0.8, radius=4)
beside('JP2', 'HOLD SRC', 'N', 0.8)
beside('J3', 'FAN 5V', 'S', 1.0, bold=True)

# ---- MMDVM block
beside('SW1', 'RESET', 'S', 0.8)
beside('JP1', 'BOOT1', 'W', 0.8)
beside('TP3', 'D-', 'N', 0.8)
beside('TP4', 'D+', 'N', 0.8)
beside('J5', 'TJC DISPLAY', 'S', 1.0, bold=True)
for num, name in (('1', 'GND'), ('2', 'TX'), ('3', 'RX'), ('4', '5V')):
    x, y = pad('J5', num)
    label(name, x, bb('J5')[1] - 0.9, 0.8, radius=3.0)
beside('P5', 'SWD', 'E', 0.8)
for num, name in (('1', 'GND'), ('2', 'CLK'), ('3', 'DIO'), ('4', '3V3')):
    x, y = pad('P5', num)
    label(name, x, bb('P5')[3] + 0.9, 0.8, radius=3.0)
x0, y0, x1, y1 = bb('P7')
label('+ BOOT1 -', (x0 + x1) / 2, y0 - 0.9, 0.8)
label('+ BOOT0 -', (x0 + x1) / 2, y1 + 0.9, 0.8)

# ---- title block (front) and notes (back)
label('MMDVM_HS_Dual_Hat', 114.5, 176.0, 1.5, radius=12, bold=True)
label('+ Meshtastic + GPS', 114.5, 178.6, 1.2, radius=12)
label('r3.0 study  2026-11', 114.5, 180.9, 1.0, radius=12)
label('for Bubblegum-96 (96Boards CE)', 114.5, 183.0, 0.8, radius=25)
label('based on r1.3 by DB9MAT DF2ET DO7EN', 124.0, 185.0, 0.8, radius=14)
label('96Boards LS 1.8 V', 129.0, 207.5, 1.0, back=True, radius=8, bold=True)
if 'J10' in fps:
    label('96Boards HS (USB)', 132.75, 240.5, 1.0, back=True, radius=8, bold=True)
label('4 x 18650 in PARALLEL (1S4P)', 143.0, 105.0, 1.2, back=True, radius=10, bold=True)
label('OBSERVE POLARITY (+ MARKS)', 143.0, 199.5, 1.0, back=True, radius=14)

board.Save(PCB)
print('labels placed', placed, '| skipped', skipped)
sys.stdout.flush()
os._exit(0)
