"""Close whatever DRC still lists as unconnected, one connection at a time (KiCad's python).

Each round: run DRC, then for every unconnected item pair call patch_route.py between the two reported
positions; a ground pad or island that only misses the plane gets a via (`VIA` mode). Stops when nothing is
left or a round makes no progress.

Usage: python auto_patch.py [rounds]
"""
import json
import os
import subprocess
import sys
import tempfile

import main_pcb as M

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
JS = os.path.join(tempfile.gettempdir(), 'auto_patch_drc.json')


def drc():
    subprocess.run([M.KCLI, 'pcb', 'drc', '--schematic-parity', '--severity-all', '--format', 'json', '-o', JS, PCB],
                   capture_output=True)
    return json.load(open(JS, encoding='utf-8'))['unconnected_items']


last = None
for rnd in range(int(sys.argv[1]) if len(sys.argv) > 1 else 4):
    items = drc()
    print('round', rnd + 1, 'unconnected', len(items))
    if not items or len(items) == last:
        break
    last = len(items)
    for it in items:
        a, b = it['items'][0], it['items'][1]
        zone = [x for x in (a, b) if x['pos']['x'] == 100.0 and x['pos']['y'] == 251.0 or 'GND' in x['description']
                and ('區域' in x['description'] or 'Zone' in x['description'])]
        other = [x for x in (a, b) if x not in zone]
        if zone and other and '[GND]' not in other[0]['description']:
            continue
        if zone and other:
            args = ['@%.4f,%.4f,ANY' % (other[0]['pos']['x'], other[0]['pos']['y']), 'VIA']
        elif zone:
            continue                      # island to island: needs a pad, handled by force_gnd.py
        else:
            args = ['@%.4f,%.4f,ANY' % (a['pos']['x'], a['pos']['y']), '@%.4f,%.4f,ANY' % (b['pos']['x'], b['pos']['y'])]
        r = subprocess.run([sys.executable, os.path.join(HERE, 'patch_route.py')] + args, capture_output=True, text=True)
        out = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith(('routed', 'NO PATH', 'no track', '   reached'))
               or 'Error' in ln]
        print('  ', ' | '.join(out)[:170])
sys.stdout.flush()
os._exit(0)
