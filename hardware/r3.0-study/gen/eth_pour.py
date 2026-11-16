"""Add a +1V2_ETH pour on B.Cu under the LAN7500 (run with KiCad's python, after routing).

The 1.2 V core rail (about 0.5 A) reaches several pins through thin escapes; the pour fills the free bottom
copper under and around the controller and ties the rail's vias together in parallel. It has priority over
the ground pour only inside this rectangle; run DRC afterwards to confirm no ground island was cut off.

Usage: python eth_pour.py
"""
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
for z in list(board.Zones()):
    if z.GetZoneName() == 'ETH_1V2':
        board.Remove(z)
u = [f for f in board.GetFootprints() if f.GetReference() == 'U60'][0]
c = M.court(u)
x0, y0, x1, y1 = c[0] - 2.5, c[1] - 2.5, c[2] + 0.5, c[3] + 2.5
z = pcbnew.ZONE(board)
z.SetLayer(pcbnew.B_Cu)
z.SetNet(board.FindNet('+1V2_ETH'))
z.SetZoneName('ETH_1V2')
ol = z.Outline()
ol.NewOutline()
for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
    ol.Append(mm(M.X0 + x), mm(M.Y0 - y))
z.SetLocalClearance(mm(0.2))
z.SetMinThickness(mm(0.25))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
z.SetAssignedPriority(3)
board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
vias = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == '+1V2_ETH'
           and z.HitTestFilledArea(pcbnew.B_Cu, t.GetPosition()))
print('+1V2_ETH pour on B.Cu: %.0f mm2, rail vias inside it: %d' % (z.GetFilledArea() / 1e12, vias))
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
