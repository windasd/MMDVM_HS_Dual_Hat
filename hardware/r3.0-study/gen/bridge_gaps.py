"""Close short gaps the autorouter left: join two same-net items with one straight segment when the path is free.

Usage: python bridge_gaps.py <drc.json>   (run after route.py import; then re-run DRC)
"""
import json
import math
import os
import re
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
drc = json.load(open(sys.argv[1], encoding='utf-8'))
mm = pcbnew.FromMM
MAXLEN, W, CL = 4.0, 0.2, 0.13
pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
tracks = list(board.GetTracks())
LAYERS = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu, 'In1.Cu': pcbnew.In1_Cu, 'In2.Cu': pcbnew.In2_Cu}


def find(item):
    """-> (net, [(point, layers)]) for a DRC item, or None for zones / unknown items."""
    d = item['description']
    m = re.search(r'\[([^\]]+)\]', d)
    if not m or '區域' in d:
        return None
    net = m.group(1)
    q = pcbnew.VECTOR2I(mm(item['pos']['x']), mm(item['pos']['y']))
    for t in tracks:
        if t.GetNetname() != net or not t.HitTest(q, mm(0.03)):
            continue
        if t.GetClass() == 'PCB_VIA':
            return net, [(t.GetPosition(), (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu))]
        if any(name in d and t.GetLayer() == lay for name, lay in LAYERS.items()):
            return net, [(t.GetStart(), (t.GetLayer(),)), (t.GetEnd(), (t.GetLayer(),))]
    for p in pads:
        if p.GetNetname() == net and p.HitTest(q, mm(0.03)):
            lays = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu) if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else \
                ((pcbnew.F_Cu,) if p.IsOnLayer(pcbnew.F_Cu) else (pcbnew.B_Cu,))
            return net, [(p.GetPosition(), lays)]
    return None


def free(a, b, layer, net):
    n = max(2, int(math.hypot(a.x - b.x, a.y - b.y) / mm(0.05)))
    acc = mm(W / 2 + CL)
    for j in range(n + 1):
        q = pcbnew.VECTOR2I(int(a.x + (b.x - a.x) * j / n), int(a.y + (b.y - a.y) * j / n))
        for p in pads:
            if p.GetNetname() != net and (p.IsOnLayer(layer) or p.GetAttribute() in
                                          (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)) and p.HitTest(q, acc):
                return False
        for t in tracks:
            if t.GetNetname() != net and (t.GetClass() == 'PCB_VIA' or t.GetLayer() == layer) and t.HitTest(q, acc):
                return False
    return True


done = 0
for it in drc['unconnected_items']:
    ends = [find(i) for i in it['items'][:2]]
    if len(ends) < 2 or None in ends or ends[0][0] != ends[1][0]:
        continue
    net = ends[0][0]
    best = None
    for (pa, la) in ends[0][1]:
        for (pb, lb) in ends[1][1]:
            common = [x for x in la if x in lb]
            dist = math.hypot(pa.x - pb.x, pa.y - pb.y)
            if common and 0 < dist <= mm(MAXLEN) and (best is None or dist < best[0]):
                best = (dist, pa, pb, common)
    if not best:
        print('no straight candidate:', net, [i['description'][:40] for i in it['items']])
        continue
    for layer in best[3]:
        if free(best[1], best[2], layer, net):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(best[1]); t.SetEnd(best[2]); t.SetWidth(mm(W)); t.SetLayer(layer)
            t.SetNet(board.FindNet(net))
            board.Add(t)
            tracks.append(t)
            done += 1
            print('bridged', net, round(pcbnew.ToMM(int(best[0])), 2), 'mm on', board.GetLayerName(layer))
            break
    else:
        print('blocked:', net, round(pcbnew.ToMM(int(best[0])), 2), 'mm')
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('gaps bridged', done)
sys.stdout.flush()
os._exit(0)
