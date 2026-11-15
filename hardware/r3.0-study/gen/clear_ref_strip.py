"""Take tracks out of the reserved USB reference strip on In2 and re-route them around it.

The autorouter does not honour the rule area on the inner layer. Every unlocked In2 segment inside the strip
is removed; patch_route.py (which treats the strip as an obstacle) then reconnects its two ends.

Usage: python clear_ref_strip.py
"""
import os
import subprocess
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
HERE = os.path.dirname(os.path.abspath(__file__))
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
areas = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == 'USB_REF']
jobs, kill = [], []
if areas:
    ol = areas[0].Outline()
    for t in board.GetTracks():
        if t.GetClass() != 'PCB_TRACK' or t.GetLayer() != pcbnew.In2_Cu or t.IsLocked():
            continue
        a, e = t.GetStart(), t.GetEnd()
        n = max(1, int(t.GetLength() / mm(0.1)))
        inside = any(ol.Contains(pcbnew.VECTOR2I(int(a.x + (e.x - a.x) * k / n), int(a.y + (e.y - a.y) * k / n)), -1,
                                 t.GetWidth() // 2) for k in range(n + 1))
        if inside:
            kill.append(t)
            jobs.append((t.GetNetname(), pcbnew.ToMM(a.x), pcbnew.ToMM(a.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)))
for t in kill:
    board.Remove(t)
board.Save(PCB)
print('segments removed from the strip:', len(kill))
ok = bad = 0
for net, x1, y1, x2, y2 in jobs:
    r = subprocess.run([sys.executable, os.path.join(HERE, 'patch_route.py'),
                        '@%.4f,%.4f,ANY' % (x1, y1), '@%.4f,%.4f,ANY' % (x2, y2)], capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith(('routed', 'NO PATH', 'no track'))]
    line = line[-1] if line else (r.stdout + r.stderr).strip().splitlines()[-1:]
    print(net, '|', line)
    ok += str(line).startswith('routed')
    bad += not str(line).startswith('routed')
print('re-routed', ok, 'failed', bad)
sys.stdout.flush()
os._exit(0)
