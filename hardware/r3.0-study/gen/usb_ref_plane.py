"""Fill the reserved strip on In2 under the USB pair with ground (run with KiCad's python, after routing).

pair_route.py leaves a rule area called USB_REF on In2 (no tracks) along the USB pair on B.Cu and ground vias
beside the pair. This adds a GND zone with the same outline, so the pair has a reference plane 0.21 mm away,
like the pairs on F.Cu have with In1.

Usage: python usb_ref_plane.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
areas = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == 'USB_REF']
old = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() == 'USB_REF_GND']
if not areas:
    print('no USB_REF rule area on this board')
    sys.stdout.flush()
    os._exit(0)
src = areas[0].Outline().COutline(0)
pts = [(src.CPoint(i).x, src.CPoint(i).y) for i in range(src.PointCount())]
z = pcbnew.ZONE(board)
z.SetLayer(pcbnew.In2_Cu)
z.SetNet(board.FindNet('GND'))
z.SetZoneName('USB_REF_GND')
ol = z.Outline()
ol.NewOutline()
for x, y in pts:
    ol.Append(x, y)
z.SetLocalClearance(mm(0.2))
z.SetMinThickness(mm(0.2))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
z.SetAssignedPriority(5)
board.Add(z)
# The autorouter ignores the rule area on the inner layer and a strip this long has to be crossed somewhere,
# so tracks that cross it stay (the fill opens around them); the rule area is dropped to stop DRC flagging them.
ol_ = areas[0].Outline()
cross = 0
for t in board.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.In2_Cu and t.GetNetname() != 'GND':
        a_, e_ = t.GetStart(), t.GetEnd()
        n_ = max(1, int(t.GetLength() / mm(0.1)))
        if any(ol_.Contains(pcbnew.VECTOR2I(int(a_.x + (e_.x - a_.x) * k / n_), int(a_.y + (e_.y - a_.y) * k / n_)))
               for k in range(n_ + 1)):
            cross += 1
print('In2 track segments crossing the strip (gaps in the reference):', cross)
board.Remove(areas[0])
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
print('USB reference ground on In2: %.0f mm2 filled (outline %d points); older copies left in place: %d'
      % (z.GetFilledArea() / 1e12, len(pts), len(old)))
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
