"""Work out the JLCPCB placement-angle correction of every BOM part from JLCPCB's own footprints.

JLCPCB turns a part by the CPL angle starting from the orientation of the footprint in its (EasyEDA / LCSC)
library, which is often not the orientation of the KiCad footprint. For each LCSC number of ../BOM.csv this
script fetches the library footprint, matches its pads to the pads of the KiCad footprint on the board by pad
number, and finds the quarter turn that maps one onto the other. The result goes to jlc_rotations.json:

    {"C47616": {"corr": 270, "fit": 0.08, "pads": 8, "footprint": "VSON-8_..."} , ...}

corr is added to the KiCad angle of top-side parts by jlc_files.py. `fit` is the RMS pad distance in mm after
the turn; a part is only corrected when the fit is good and the next-best turn is clearly worse. Two-pad parts
are never corrected (their pad numbers are not a physical reference); the polarised ones are listed for a
manual check. Run with KiCad's python (needs network access):

    python jlc_rotation.py [--refresh]
"""
import csv
import json
import math
import os
import re
import sys
import time
import urllib.request

import pcbnew

import main_pcb as M

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '..', 'route', 'easyeda')
OUT = os.path.join(HERE, 'jlc_rotations.json')
URL = 'https://easyeda.com/api/products/%s/svgs'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
       'Referer': 'https://easyeda.com/editor'}
os.makedirs(CACHE, exist_ok=True)


def library_pads(code):
    """{pad number: [(x, y) mm, ...]} of the library footprint, y down, or None."""
    f = os.path.join(CACHE, code + '.json')
    if '--refresh' in sys.argv or not os.path.exists(f):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(URL % code, headers=HDR), timeout=30).read()
        except Exception as e:                   # noqa: BLE001
            return None, 'fetch failed: %s' % e
        open(f, 'wb').write(raw)
        time.sleep(0.2)
    try:
        res = json.load(open(f, encoding='utf-8')).get('result') or []
    except ValueError:
        return None, 'bad answer'
    fp = [r for r in res if r.get('docType') == 4]
    if not fp:
        return None, 'no footprint in the library'
    pads = {}
    for g in re.findall(r'<g[^>]*c_partid="part_pad"[^>]*>', fp[0]['svg']):
        num = re.search(r'number="([^"]*)"', g)
        org = re.search(r'c_origin="([-\d.]+),([-\d.]+)"', g)
        if num and org:
            pads.setdefault(num.group(1), []).append((float(org.group(1)) * 0.254, float(org.group(2)) * 0.254))
    return pads, ''


def centred(pads):
    return pads                                    # the fit below finds the shift itself


def norm(pads):
    """Library pads are sometimes named P1, P2 ...: compare by the number."""
    out = {}
    for k, v in pads.items():
        m = re.fullmatch(r'[A-Za-z]{1,2}(\d+)', k)
        out.setdefault(m.group(1) if m else k, []).extend(v)
    return out


def fit(lib, kic):
    """For each quarter turn (counter-clockwise as seen on screen, y down): spread of the pad-to-pad offsets.

    The two footprints need not share an origin, and their exposed pads are often numbered differently, so the
    shift is the median offset and the score is the RMS of the best three quarters of the pads."""
    lib = norm(lib)
    out = {}
    common = [k for k in kic if k in lib]
    if len(common) < 2:
        return None
    for ang in (0, 90, 180, 270):
        c, s = round(math.cos(math.radians(ang))), round(math.sin(math.radians(ang)))
        turned = {k: [(lx * c + ly * s, -lx * s + ly * c) for lx, ly in lib[k]] for k in common}
        # first guess of the shift from the centroids, then the nearest instance of each pad
        mk = [sum(v) / len(v) for v in zip(*[p for k in common for p in kic[k]])]
        ml = [sum(v) / len(v) for v in zip(*[p for k in common for p in turned[k]])]
        sh = (mk[0] - ml[0], mk[1] - ml[1])
        for _ in range(3):
            offs = []
            for k in common:
                for (x, y) in kic[k]:
                    q = min(turned[k], key=lambda t: math.hypot(x - t[0] - sh[0], y - t[1] - sh[1]))
                    offs.append((x - q[0], y - q[1]))
            xs, ys = sorted(o[0] for o in offs), sorted(o[1] for o in offs)
            sh = (xs[len(xs) // 2], ys[len(ys) // 2])
        res = sorted(math.hypot(o[0] - sh[0], o[1] - sh[1]) for o in offs)
        keep = res[:max(2, int(len(res) * 0.75 + 0.5))]
        out[ang] = math.sqrt(sum(r * r for r in keep) / len(keep))
    return out, len(common)


board = pcbnew.LoadBoard(os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb'))
fps = {f.GetReference(): f for f in board.GetFootprints()}
rows = list(csv.DictReader(open(os.path.join(HERE, '..', 'BOM.csv'), encoding='utf-8-sig')))
res = {}
for r in rows:
    code, ref = r['LCSC'].strip(), r['Reference'].split(',')[0]
    fp = fps.get(ref)
    if not code or fp is None:
        continue
    # KiCad pads in footprint coordinates (rotation and flip removed), y down
    rot = math.radians(fp.GetOrientationDegrees())
    o = fp.GetPosition()
    kic = {}
    for p in fp.Pads():
        if not p.GetNumber():
            continue
        dx, dy = pcbnew.ToMM(p.GetPosition().x - o.x), pcbnew.ToMM(p.GetPosition().y - o.y)
        if fp.IsFlipped():
            dx = -dx                                # KiCad mirrors a flipped footprint about its Y axis
            x, y = dx * math.cos(-rot) - dy * math.sin(-rot), dx * math.sin(-rot) + dy * math.cos(-rot)
        else:
            x, y = dx * math.cos(rot) - dy * math.sin(rot), dx * math.sin(rot) + dy * math.cos(rot)
        kic.setdefault(p.GetNumber(), []).append((x, y))
    name = fp.GetFPID().GetUniStringLibItemName()
    if len(kic) <= 2:
        # pad numbers of two-terminal parts are not a physical reference (KiCad numbers a diode's cathode 1,
        # other libraries the anode): never corrected here, polarised ones are checked by eye
        res[code] = dict(corr=None, note='two-pad part', footprint=name, ref=ref)
        continue
    lib, why = library_pads(code)
    if not lib or len(kic) < 2:
        res[code] = dict(corr=None, note=why or 'fewer than two numbered pads', footprint=name, ref=ref)
        continue
    got = fit(centred(lib), centred(kic))
    if not got:
        res[code] = dict(corr=None, note='pad numbers do not match (%s / %s)' % (sorted(lib)[:4], sorted(kic)[:4]), footprint=name, ref=ref)
        continue
    errs, n = got
    best = min(errs, key=errs.get)
    rest = sorted(v for k, v in errs.items() if k != best)
    note = ''
    if errs[best] > 0.35:
        note = 'poor fit: the library footprint differs'
    elif rest[0] - errs[best] < 0.15:
        note = 'symmetric: %s fit equally' % sorted(k for k, v in errs.items() if v - errs[best] < 0.15)
    res[code] = dict(corr=best if not note else None, fit=round(errs[best], 3), pads=n, note=note, footprint=name, ref=ref,
                     all={str(k): round(v, 2) for k, v in errs.items()})
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)
ok = [c for c, v in res.items() if v['corr'] is not None]
print('parts: %d, angle found: %d (turned: %d), not decided: %d' % (
    len(res), len(ok), sum(1 for c in ok if res[c]['corr']), len(res) - len(ok)))
for c, v in sorted(res.items(), key=lambda kv: kv[1]['footprint']):
    if v['corr'] is None and not v.get('note', '').startswith(('symmetric', 'two-pad')):
        print('  %-10s %-6s %-46s %s' % (c, v['ref'], v['footprint'][:46], v.get('note')))
sys.stdout.flush()
os._exit(0)
