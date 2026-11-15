"""Prepare a "fill the gaps" autorouter run on an already routed board.

- removes tracks that run closer than 0.45 mm to the board outline (and those named in a DRC json),
- locks every remaining track so the router only adds the missing connections,
- exports ../route/mmdvm_mesh.dsn with In1 as a power layer and the outline inset by 0.5 mm.

Usage: python reroute_prep.py [drc.json] [reference.kicad_pcb]
(with a reference board only its tracks stay locked, so the router may rip up and retry the rest)
"""
import json
import os
import re
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
DSN = os.path.join(M.PRJ, 'route', 'mmdvm_mesh.dsn')
os.makedirs(os.path.dirname(DSN), exist_ok=True)
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
tracks = list(board.GetTracks())
kill = set()
JS = [a_ for a_ in sys.argv[1:] if a_.endswith('.json')]
if JS:
    drc = json.load(open(JS[0], encoding='utf-8'))
    for v in drc['violations']:
        if v['type'] != 'copper_edge_clearance':
            continue
        for i in v['items']:
            q = pcbnew.VECTOR2I(mm(i['pos']['x']), mm(i['pos']['y']))
            for k, t in enumerate(tracks):
                if t.GetClass() == 'PCB_TRACK' and ('[' + t.GetNetname() + ']') in i['description'] \
                        and t.HitTest(q, mm(0.02)):
                    kill.add(k)


def near_edge(q, lim=0.45):
    x, y = M.model(q)
    poly = M.OUTLINE
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if x1 == x2 and min(y1, y2) - 0.1 <= y <= max(y1, y2) + 0.1 and abs(x - x1) < lim:
            return True
        if y1 == y2 and min(x1, x2) - 0.1 <= x <= max(x1, x2) + 0.1 and abs(y - y1) < lim:
            return True
    return False


for k, t in enumerate(tracks):
    if t.GetClass() == 'PCB_TRACK' and not t.IsLocked() and (near_edge(t.GetStart()) or near_edge(t.GetEnd())):
        kill.add(k)
for k in kill:
    board.Remove(tracks[k])
REF = [a_ for a_ in sys.argv[1:] if a_.endswith('.kicad_pcb')]


def key(t):
    if t.GetClass() == 'PCB_VIA':
        return ('v', t.GetPosition().x, t.GetPosition().y)
    e = sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)])
    return (t.GetLayer(), e[0], e[1])


if REF:      # lock only the tracks that also exist in the reference board (the r1.3 block); free the rest
    keep = {key(t) for t in pcbnew.LoadBoard(REF[0]).GetTracks()}
    nlock = 0
    for t in board.GetTracks():
        t.SetLocked(key(t) in keep)
        nlock += key(t) in keep
else:
    nlock = len(board.GetTracks())
    for t in board.GetTracks():
        t.SetLocked(True)
board.Save(PCB)
print('removed', len(kill), 'edge-hugging tracks; locked', nlock, 'of', len(board.GetTracks()))
print('export', pcbnew.ExportSpecctraDSN(board, DSN))
s = open(DSN, 'rb').read()
s = re.sub(rb'(\(layer In1\.Cu\s*\(type )signal', rb'\1power', s, count=1)
poly = M.OUTLINE
n = len(poly)


def nrm(a, b):                      # inward normal of a CCW polygon edge
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = (dx * dx + dy * dy) ** 0.5
    return -dy / length, dx / length


ip = []
for k in range(n):
    n1, n2 = nrm(poly[k - 1], poly[k]), nrm(poly[k], poly[(k + 1) % n])
    ip.append((poly[k][0] + 0.5 * (n1[0] + n2[0]), poly[k][1] + 0.5 * (n1[1] + n2[1])))
txt = ' '.join('%d %d' % (round((M.X0 + x) * 1000), round(-(M.Y0 - y) * 1000)) for x, y in ip + ip[:1])
s2 = re.sub(rb'\(boundary\s*\(path pcb 0[^)]*\)', ('(boundary\n      (path pcb 0  ' + txt + ')').encode(), s, count=1)
open(DSN, 'wb').write(s2)
print('outline inset in DSN:', s2 != s)
sys.stdout.flush()
os._exit(0)
