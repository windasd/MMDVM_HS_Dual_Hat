"""Clear the inner layers under a chip: take other nets' In2 / B.Cu copper out of a box and route it again around
the box (run with any python 3; it drives KiCad's python for the board work).

Used for U60 (LAN7500): its exposed pad is its only VSS, and its power pins need fan-out vias with capacitors on
the bottom side, but the autorouter had run power-path and signal tracks of other nets straight under it.

A "section" of a net is its In2 / B.Cu tracks and vias that touch the box, grown along the copper until it leaves
the box (a junction, via or pad outside the box ends it; inside the box the walk goes on through vias and
branches). The section is removed and its attachment points (where it met the copper that stays) are joined
again with patch_route.py, with the box forbidden for tracks on In2 / B.Cu (and F.Cu with --front) and for vias.
A net is put back as it was if the new route is longer than the removed copper by more than --extra mm, adds more
than --vias vias, or cannot be found.

Tried on U60 on 2026-11-26 (design record 16.24) and not kept: the space under U60 is the only corridor between
the chip and the top end of the USB reference strip, so the nets moved out of it had to cut the strip.
After a run, check DRC (patch_route.py keeps only 0.1 mm from non-plated holes; the rule is 0.2 mm), copper-pour
islands it may cut off, and the strip (stitch_strip.py --dry lists its cuts).

Usage: python clear_under.py list  x0,y0,x1,y1 [--own x0,y0,x1,y1] [--skip NET,NET]
       python clear_under.py run   x0,y0,x1,y1 [--own ...] [--skip ...] [--extra 20] [--vias 3] [--front]
                                   [--avoid 'LAYER:x0,y0,x1,y1;...'] [NET ...]
`--own`: nets of the chip itself (any pad of REF, see --ref) are only cleared out of this smaller box.
`--avoid`: more PR_AVOID boxes for the new routes. Always pass the In2 reference strip under the USB pair
(In2.Cu:147.8,99,150.4,204 and VIA on it): it is not a rule area, so the router does not know it otherwise.
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
PCB = os.path.join(HERE, '..', 'mmdvm_mesh.kicad_pcb')
JS = os.path.join(HERE, '..', 'route', 'clear_under.json')

ANALYSE = r'''
import os, sys, math, json
from collections import defaultdict
import pcbnew
import main_pcb as M
b = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')); mm = pcbnew.ToMM
BOX, OWN, REF, SKIP, OUT = %r, %r, %r, %r, %r
IN = (pcbnew.In2_Cu, pcbnew.B_Cu)
def k(p): return (round(mm(p.x), 3), round(mm(p.y), 3))
def dseg(p, a, e):
    dx, dy = e[0] - a[0], e[1] - a[1]
    L2 = dx * dx + dy * dy
    u = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)
def inbox(p, bx, m=0.0): return bx[0] - m <= p[0] <= bx[2] + m and bx[1] - m <= p[1] <= bx[3] + m
def seg_hits(a, e, bx):
    # sampled: good enough for boxes a few mm across
    n = max(1, int(math.hypot(e[0] - a[0], e[1] - a[1]) / 0.05))
    return any(inbox((a[0] + (e[0] - a[0]) * i / n, a[1] + (e[1] - a[1]) * i / n), bx) for i in range(n + 1))
own = {p.GetNetname() for p in b.FindFootprintByReference(REF).Pads()} if REF else set()
trk = defaultdict(list); via = defaultdict(list)
for t in b.GetTracks():
    n = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        via[n].append(k(t.GetPosition()))
    elif t.GetStart() != t.GetEnd():
        trk[n].append((b.GetLayerName(t.GetLayer()), k(t.GetStart()), k(t.GetEnd()), round(mm(t.GetWidth()), 3), t.GetLayer() in IN))
pads = defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname():
            bb = p.GetBoundingBox()
            pads[p.GetNetname()].append((mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()), p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, f.IsFlipped()))
out = []
for net in sorted(set(trk) | set(via)):
    if net in ('GND', '') or net in SKIP:
        continue
    bx = OWN if (net in own and OWN) else BOX
    T, V = trk[net], via[net]
    start = [i for i, s in enumerate(T) if s[4] and seg_hits(s[1], s[2], bx)]
    vstart = [v for v in V if inbox(v, bx)]
    if not start and not vstart:
        continue
    # grow the section
    secT, secV = set(start), set(vstart)
    def touching(pt, layer=None):
        """items at a point: (tracks idx, vias, pads)"""
        ts = [i for i, s in enumerate(T) if (s[1] == pt or s[2] == pt) and (layer is None or s[0] == layer)]
        # a track end in the middle of another track (T junction)
        ts += [i for i, s in enumerate(T) if i not in ts and (layer is None or s[0] == layer) and dseg(pt, s[1], s[2]) < 0.01]
        vs = [v for v in V if math.hypot(v[0] - pt[0], v[1] - pt[1]) < 0.01]
        ps = [p for p in pads[net] if p[0] - 0.01 <= pt[0] <= p[2] + 0.01 and p[1] - 0.01 <= pt[1] <= p[3] + 0.01]
        return ts, vs, ps
    attach = {}
    changed = True
    while changed:
        changed = False
        pts = set()
        for i in secT:
            pts.add((T[i][1], T[i][0])); pts.add((T[i][2], T[i][0]))
        for v in secV:
            pts.add((v, 'VIA'))
        for pt, layer in pts:
            if layer == 'VIA':
                ts, vs, ps = touching(pt)
                # a via of the section: everything on it goes with it, F.Cu tracks become attachment points
                for i in ts:
                    if T[i][4] and i not in secT:
                        secT.add(i); changed = True
                    elif not T[i][4]:
                        attach[(pt, T[i][0])] = 'track'
                for p in ps:
                    attach[(pt, 'PAD')] = 'pad'
                continue
            ts, vs, ps = touching(pt, layer)
            others = [i for i in ts if i not in secT]
            inside = inbox(pt, bx, 0.3)
            if vs and not any(v in secV for v in vs):
                if inside:
                    secV.update(vs); changed = True
                else:
                    attach[(pt, 'ANY')] = 'via'
            if ps:
                attach[(pt, 'PAD')] = 'pad'
            if others:
                deg = len([i for i in ts])
                if inside or (deg == 2 and not vs and not ps):
                    secT.update(others); changed = True
                else:
                    attach[(pt, layer)] = 'junction'
        # dead ends are fine (removed with the section)
    # attachment points that lie on section copper only through removed items are the real ends
    ends = []
    for (pt, layer), kind in attach.items():
        if layer == 'VIA':
            continue
        ends.append(dict(pt=pt, layer=layer, kind=kind))
    # drop duplicate points (same spot, several labels): prefer a concrete layer
    seen = {}
    for e in ends:
        key = e['pt']
        if key not in seen or seen[key]['layer'] in ('ANY', 'PAD'):
            seen[key] = e
    ends = list(seen.values())
    L = sum(math.hypot(T[i][2][0] - T[i][1][0], T[i][2][1] - T[i][1][1]) for i in secT)
    out.append(dict(net=net, own=net in own, segs=[T[i][:4] for i in sorted(secT)], vias=sorted(secV), ends=ends, length=round(L, 2),
                    w=min([T[i][3] for i in secT] or [0.2])))
json.dump(out, open(OUT, 'w'), indent=1)
for c in out:
    print('%%-26s %%s removes %%5.1f mm, %%2d segs, %%d vias; %%d ends: %%s' %% (c['net'][-26:], 'own' if c['own'] else '   ', c['length'], len(c['segs']), len(c['vias']), len(c['ends']),
          ' '.join('%%s@%%g,%%g(%%s)' %% (e['kind'], e['pt'][0], e['pt'][1], e['layer']) for e in c['ends'])))
sys.stdout.flush(); os._exit(0)
'''


def kpy(*args, env=None):
    e = dict(os.environ, MSYS_NO_PATHCONV='1')
    e.update(env or {})
    r = subprocess.run([KPY] + list(args), cwd=HERE, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout + r.stderr


def box(s):
    return tuple(float(v) for v in s.split(','))


def opts(a):
    o = dict(own=None, skip=[], extra=20.0, vias=3, front=False, ref='U60', nets=[], avoid='')
    a = list(a)
    while a:
        x = a.pop(0)
        if x == '--own':
            o['own'] = box(a.pop(0))
        elif x == '--skip':
            o['skip'] = a.pop(0).split(',')
        elif x == '--extra':
            o['extra'] = float(a.pop(0))
        elif x == '--vias':
            o['vias'] = int(a.pop(0))
        elif x == '--front':
            o['front'] = True
        elif x == '--avoid':
            o['avoid'] = a.pop(0)
        elif x == '--ref':
            o['ref'] = a.pop(0)
        else:
            o['nets'].append(x)
    return o


def analyse(bx, o):
    os.makedirs(os.path.dirname(JS), exist_ok=True)
    print(kpy('-c', ANALYSE % (bx, o['own'], o['ref'], o['skip'], JS)).strip())


def run(bx, o):
    analyse(bx, o)
    todo = json.load(open(JS))
    if o['nets']:
        todo = [c for c in todo if c['net'] in o['nets']]
    ok = bad = 0
    for c in todo:
        net, ends = c['net'], c['ends']
        b2 = o['own'] if (c['own'] and o['own']) else bx
        if len(ends) != 2:
            print('%-26s %d ends: skipped (join by hand)' % (net[-26:], len(ends)), flush=True)
            bad += 1
            continue
        f = os.path.join(HERE, '..', 'route', 'clear_%s.txt' % re.sub(r'[^A-Za-z0-9]+', '_', net))
        with open(f, 'w') as fh:
            for layer, a, e, w in c['segs']:
                fh.write('RM %s %g,%g %g,%g\n' % (layer, a[0], a[1], e[0], e[1]))
            for v in c['vias']:
                fh.write('RMVIA %g,%g\n' % tuple(v))
        shutil.copyfile(PCB, PCB + '.clear')
        o1 = kpy('hand_edit.py', f, 'rm')
        want = len(c['segs']) + len(c['vias'])
        if 'removed %d of %d' % (want, want) not in o1:
            shutil.copyfile(PCB + '.clear', PCB)
            print('%-26s could not take the section out: %s' % (net[-26:], o1.strip().splitlines()[-1:]), flush=True)
            bad += 1
            continue
        spec = ['@%g,%g,%s' % (e['pt'][0], e['pt'][1], 'ANY' if e['layer'] in ('ANY', 'PAD') else e['layer']) for e in ends]
        bs = '%g,%g,%g,%g' % b2
        avoid = 'In2.Cu:%s;B.Cu:%s;VIA:%s' % (bs, bs, bs) + (';F.Cu:%s' % bs if o['front'] else '') + (';' + o['avoid'] if o['avoid'] else '')
        out = kpy('patch_route.py', *spec, env={'PR_AVOID': avoid, 'PR_MARGIN': '12', 'PR_EXIT': '0', 'PR_W': '%g' % c['w']})
        line = [ln for ln in out.splitlines() if ln.startswith(('routed', 'NO PATH'))]
        m = re.search(r': ([\d.]+) mm, \d+ segments, (\d+) vias', line[0]) if line else None
        good = bool(line and line[0].startswith('routed') and (' ' + net + ':') in line[0] and m)
        old_v = len(c['vias'])
        if good and (float(m.group(1)) > c['length'] + o['extra'] or int(m.group(2)) > old_v + o['vias']):
            good = False
            line = ['too long: %s mm and %s vias in place of %.1f mm and %d vias' % (m.group(1), m.group(2), c['length'], old_v)]
        if good:
            ok += 1
            print('%-26s %.1f mm, %d vias -> %s' % (net[-26:], c['length'], old_v, line[0].split('  ')[-1]), flush=True)
        else:
            shutil.copyfile(PCB + '.clear', PCB)
            bad += 1
            print('%-26s kept (%s)' % (net[-26:], (line or out.strip().splitlines()[-1:] or ['?'])[0][:90]), flush=True)
    if os.path.exists(PCB + '.clear'):
        os.remove(PCB + '.clear')
    print('moved out of the box: %d, kept: %d' % (ok, bad))


if __name__ == '__main__':
    mode, bx, o = sys.argv[1], box(sys.argv[2]), opts(sys.argv[3:])
    if mode == 'list':
        analyse(bx, o)
    else:
        run(bx, o)
