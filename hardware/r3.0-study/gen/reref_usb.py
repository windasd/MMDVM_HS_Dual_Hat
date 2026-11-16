"""Take the In2 tracks of other nets out of the ground strip under the USB pair (run with any python 3).

The USB pair runs on B.Cu from y 99 to 204 and is referenced to a 2.6 mm ground strip on In2. Later routing
passes put signal tracks across that strip on In2, cutting it into pieces. For each crossing this script
clips the In2 track 1.2 mm either side of the strip (hand_edit.py), then asks patch_route.py to close the gap
with the strip forbidden on In2, so the connection crosses on F.Cu instead (over the In1 plane). A crossing
that cannot be re-routed is put back as it was.

Usage: python reref_usb.py list | run [n ...]      (needs crossings.json from the `list` step)
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KPY = os.environ.get('KPY', r'C:/Program Files/KiCad/10.0/bin/python.exe')
STRIP = (147.8, 99.0, 150.4, 204.0)
BAND = (STRIP[0] - 1.2, STRIP[2] + 1.2)
JS = os.path.join(HERE, '..', 'route', 'crossings.json')
PCB = os.path.join(HERE, '..', 'mmdvm_mesh.kicad_pcb')
MAX_EXTRA, MAX_VIAS = 25.0, 3            # a detour longer than the gap by more than this, or with more vias, is refused
LIST = r'''
import os, sys, math, json
from collections import defaultdict
import pcbnew
import main_pcb as M
b = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')); mm = pcbnew.ToMM
X0, Y0, X1, Y1 = %r
def k(p): return (round(mm(p.x), 3), round(mm(p.y), 3))
segs = defaultdict(list)
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.In2_Cu and t.GetNetname() != 'GND' and t.GetStart() != t.GetEnd():
        segs[t.GetNetname()].append((k(t.GetStart()), k(t.GetEnd()), mm(t.GetWidth())))
vias = defaultdict(set)
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA': vias[t.GetNetname()].add(k(t.GetPosition()))
out = []
for net, ss in segs.items():
    adj = defaultdict(list)
    for i, (a, e, w) in enumerate(ss):
        adj[a].append(i); adj[e].append(i)
    def crosses(a, e):
        xs = sorted((a[0], e[0])); ys = sorted((a[1], e[1]))
        return xs[0] < X1 and xs[1] > X0 and ys[1] > Y0 and ys[0] < Y1
    seen = set()
    for i, (a, e, w) in enumerate(ss):
        if i in seen or not crosses(a, e): continue
        # the chain as an ordered list of points, grown both ways until a via, a junction or a dead end
        seen.add(i)
        def grow(p, cur):
            pts = []
            while not (p in vias[net] or len(adj[p]) != 2):
                nxt = [j for j in adj[p] if j != cur][0]
                seen.add(nxt); cur = nxt
                p = ss[nxt][1] if ss[nxt][0] == p else ss[nxt][0]
                pts.append(p)
            return pts, ('via' if p in vias[net] else ('junction' if len(adj[p]) > 2 else 'end'))
        back, kb = grow(a, i); fwd, kf = grow(e, i)
        pts = list(reversed(back)) + [a, e] + fwd
        ws = [x[2] for x in ss if x[0] in pts and x[1] in pts]
        out.append(dict(net=net, pts=pts, kinds=[kb, kf], w=min(ws)))
out.sort(key=lambda c: min(p[1] for p in c['pts']))
json.dump(out, open(%r, 'w'))
print('In2 chains of other nets through the strip:', len(out), 'nets:', len({c['net'] for c in out}))
sys.stdout.flush(); os._exit(0)
'''


def kpy(*args, env=None):
    e = dict(os.environ, MSYS_NO_PATHCONV='1')
    e.update(env or {})
    r = subprocess.run([KPY] + list(args), cwd=HERE, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout + r.stderr


def listing():
    os.makedirs(os.path.dirname(JS), exist_ok=True)
    print(kpy('-c', LIST % (STRIP, JS)).strip().splitlines()[-1])


def cut(pts):
    """Split the chain at the band: (west part, east part, ends of the gap) - or None when it does not go through."""
    inside = [BAND[0] <= p[0] <= BAND[1] for p in pts]
    if not any(inside) and not any((p[0] < BAND[0]) != (q[0] < BAND[0]) for p, q in zip(pts, pts[1:])):
        return None

    def at(p, q, x):
        t = (x - p[0]) / (q[0] - p[0])
        return (round(x, 3), round(p[1] + t * (q[1] - p[1]), 3))
    # first and last index where the chain is inside or crosses the band
    def boundary(seq):
        """Walk from the start: the kept points before the band and the cut point."""
        keep = []
        for p, q in zip(seq, seq[1:]):
            side = -1 if p[0] < BAND[0] else (1 if p[0] > BAND[1] else 0)
            if side == 0:
                return keep, p, False            # the chain starts inside the band: its end is the gap end
            keep.append(p)
            lim = BAND[0] if side < 0 else BAND[1]
            if (q[0] - lim) * side < 0:          # this segment enters the band
                c = at(p, q, lim)
                return keep + [c], c, True
        return None
    w = boundary(pts)
    e = boundary(pts[::-1])
    if not w or not e:
        return None
    return w, e


def run(which):
    todo = json.load(open(JS))
    ok = bad = 0
    for i, c in enumerate(todo):
        if which and i not in which:
            continue
        pts, w, net = [tuple(p) for p in c['pts']], c['w'], c['net']
        got = cut(pts)
        ymid = sum(p[1] for p in pts) / len(pts)
        if not got:
            print('%2d %-26s skipped (does not pass through)' % (i, net[-26:]))
            bad += 1
            continue
        (keep_a, end_a, clipped_a), (keep_b, end_b, clipped_b) = got
        f = os.path.join(HERE, '..', 'route', 'reref_%d.txt' % i)
        g = os.path.join(HERE, '..', 'route', 'reref_%d_undo.txt' % i)
        with open(f, 'w') as fh, open(g, 'w') as gh:
            for p, q in zip(pts, pts[1:]):
                fh.write('RM In2.Cu %g,%g %g,%g\n' % (p + q))
            for keep in (keep_a, keep_b):
                if len(keep) > 1:
                    fh.write('T %s In2.Cu %g %s\n' % (net.replace(' ', '%20'), w, ' '.join('%g,%g' % p for p in keep)))
                    for p, q in zip(keep, keep[1:]):
                        gh.write('RM In2.Cu %g,%g %g,%g\n' % (p + q))
            gh.write('T %s In2.Cu %g %s\n' % (net.replace(' ', '%20'), w, ' '.join('%g,%g' % p for p in pts)))
        shutil.copyfile(PCB, PCB + '.reref')          # the way back if this crossing cannot be moved
        o1 = kpy('hand_edit.py', f, 'rm')
        o2 = kpy('hand_edit.py', f, 'add')
        if 'removed %d of %d' % (len(pts) - 1, len(pts) - 1) not in o1 or 'added' not in o2:
            shutil.copyfile(PCB + '.reref', PCB)
            raise SystemExit('%d %s: the clip edit failed: %s | %s' % (i, net, o1[-300:], o2[-300:]))
        # a clipped end is on the In2 stub; an end that was a via / junction keeps whatever copper is there
        spec = ['@%g,%g,%s' % (p + ('In2.Cu' if cl else 'ANY',)) for p, cl in ((end_a, clipped_a), (end_b, clipped_b))]
        out = kpy('patch_route.py', *spec, env={'PR_AVOID': 'In2.Cu:%g,%g,%g,%g' % (STRIP[0] - 0.25, STRIP[1], STRIP[2] + 0.25, STRIP[3]),
                                                'PR_MARGIN': '14', 'PR_EXIT': '0', 'PR_W': '%g' % w})
        line = [ln for ln in out.splitlines() if ln.startswith(('routed', 'NO PATH'))]
        m = re.search(r': ([\d.]+) mm, \d+ segments, (\d+) vias', line[0]) if line else None
        gap = math.hypot(end_a[0] - end_b[0], end_a[1] - end_b[1])
        if line and line[0].startswith('routed') and (' ' + net + ':') in line[0] and m and (
                float(m.group(1)) > gap + MAX_EXTRA or int(m.group(2)) > MAX_VIAS):
            # too long a detour for what it buys: take the new copper out again and put the old track back
            line = ['NO PATH (found, but %s mm and %s vias for a %.1f mm gap: not worth it)' % (m.group(1), m.group(2), gap)]
        if line and line[0].startswith('routed') and (' ' + net + ':') in line[0]:
            ok += 1
            print('%2d %-26s y %.1f  %s' % (i, net[-26:], ymid, line[0].split('  ')[-1]), flush=True)
        else:
            if line and line[0].startswith('routed'):
                raise SystemExit('%d: the router closed another net (%s) - stop and restore the board' % (i, line[0]))
            shutil.copyfile(PCB + '.reref', PCB)
            bad += 1
            print('%2d %-26s y %.1f  NOT re-routed, put back (%s)' % (i, net[-26:], ymid, (line or out.strip().splitlines()[-1:] or ['?'])[0][:70]), flush=True)
    if os.path.exists(PCB + '.reref'):
        os.remove(PCB + '.reref')
    print('re-routed off the strip: %d, left on In2: %d' % (ok, bad))


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        listing()
    else:
        run([int(v) for v in sys.argv[2:]])
