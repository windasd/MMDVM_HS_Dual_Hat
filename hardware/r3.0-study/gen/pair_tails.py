"""Connect the ends of the pre-routed differential pairs to their pins and lock the pair nets.

Run after pair_route.py (KiCad's python). Each line of a pair is taken from its free end straight to its pin
with patch_route.py (single tracks: the pins of a pair are not side by side at the RJ45, and the USB pair has
to change from B.Cu to F.Cu at the controller). Everything on the pair nets is then locked, so the autorouter
leaves it alone.

Usage: python pair_tails.py
"""
import math
import os
import subprocess
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
HERE = os.path.dirname(os.path.abspath(__file__))
board = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in board.GetFootprints()}


def pad(ref, num):
    return [p for p in fps[ref].Pads() if p.GetNumber() == num][0]


# (pin the pair starts at, pin its free end goes to)
JOBS = [(('U60', '44'), ('J60', '2')), (('U60', '43'), ('J60', '3')), (('U60', '47'), ('J60', '4')),
        (('U60', '46'), ('J60', '5')), (('U60', '52'), ('J60', '6')), (('U60', '51'), ('J60', '7')),
        (('U60', '55'), ('J60', '8')), (('U60', '54'), ('J60', '9')),
        (('J10', '51'), ('U60', '13')), (('J10', '53'), ('U60', '12'))]
import re
import shutil


def spec(src, dst):
    p0 = pad(*src)
    q0 = p0.GetPosition()
    ends = []
    for t in board.GetTracks():
        if t.GetNetname() == p0.GetNetname() and t.GetClass() == 'PCB_TRACK':
            for q in (t.GetStart(), t.GetEnd()):
                ends.append((math.hypot(q.x - q0.x, q.y - q0.y), q, t.GetLayerName()))
    _d, q, layer = max(ends, key=lambda e: e[0])
    return ['@%.4f,%.4f,%s' % (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), layer), '%s.%s' % dst]


def run(args):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'patch_route.py')] + args, capture_output=True, text=True)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith(('routed', 'NO PATH'))]
    lens = [float(m.group(1)) for m in (re.search(r': ([0-9.]+) mm', ln) for ln in lines) if m]
    return lines, (sum(lens) if len(lens) * 2 == len(args) else 1e9)


# pair by pair, trying both orders of the two lines: the line routed first can block its partner
BAK = PCB + '.tails.bak'
for k in range(0, len(JOBS), 2):
    a, b = spec(*JOBS[k]), spec(*JOBS[k + 1])
    shutil.copy(PCB, BAK)
    best = None
    for order in (a + b, b + a):
        shutil.copy(BAK, PCB)
        lines, total = run(order)
        if best is None or total < best[1]:
            best = (order, total, lines)
    if best[0] != b + a:              # the board on disk holds the second order: redo the better one
        shutil.copy(BAK, PCB)
        best = (best[0],) + run(best[0])[::-1]
        best = (best[0], best[1], best[2])
        lines = best[2]
    else:
        lines = best[2]
    for ln in lines:
        print(ln)
os.remove(BAK)
board = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in board.GetFootprints()}
# terminations sit on the bottom side at the RJ45 pins (main_pcb.py): a straight B.Cu link pin -> resistor
for ref, pin in (('R85', '2'), ('R86', '3'), ('R87', '4'), ('R88', '5'), ('R96', '6'), ('R97', '7'), ('R98', '8'),
                 ('R99', '9')):
    if ref in fps and fps[ref].IsFlipped():
        jp = pad('J60', pin)
        rp = [p for p in fps[ref].Pads() if p.GetNetname() == jp.GetNetname()][0]
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(jp.GetPosition()); t.SetEnd(rp.GetPosition()); t.SetWidth(pcbnew.FromMM(0.2))
        t.SetLayer(pcbnew.B_Cu); t.SetNet(jp.GetNet())
        board.Add(t)
n = 0
for t in board.GetTracks():
    if 'ETH_TR' in t.GetNetname() or 'HS_USB' in t.GetNetname():
        t.SetLocked(True)
        n += 1
board.Save(PCB)
print('pair nets locked:', n, 'items')
sys.stdout.flush()
os._exit(0)
