"""Set the antenna feed lines to the 50 ohm width of the JLC04161H-7628 stack-up (run with KiCad's python).

Outer copper sits 0.2104 mm above the In1 ground plane (7628 prepreg, Er about 4.4-4.6). Hammerstad-Jensen
gives 51-52 ohm for a 0.35 mm microstrip; the 0.20/0.25 mm lines inherited from the two-layer r1.3 board and
from the autorouter are 61-68 ohm here. Check the width with the JLCPCB impedance calculator before ordering.

  python rf_lines.py --strip-gps   remove the GPS feed (autorouted through In2) so it can be re-routed on F.Cu
  python rf_lines.py               widen every F.Cu segment of the feed nets, refill zones
"""
import os
import sys

import pcbnew

import main_pcb as M

W50 = 0.35
NETS = ('/Meshtastic/MESH_RF_LORA', '/Meshtastic/MESH_RF_BT', '/GPS/GPS_RF', 'Net-(P1-P1)', 'Net-(P2-P1)')
PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
if '--strip-gps' in sys.argv:
    gone = [t for t in board.GetTracks() if t.GetNetname() == '/GPS/GPS_RF']
    for t in gone:
        board.Remove(t)
    print('GPS feed removed:', len(gone), 'items')
else:
    n = 0
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_TRACK' and t.GetNetname() in NETS:
            if t.GetLayer() != pcbnew.F_Cu:
                print('WARNING: %s still has a segment on %s' % (t.GetNetname(), t.GetLayerName()))
            elif t.GetWidth() != pcbnew.FromMM(W50):
                t.SetWidth(pcbnew.FromMM(W50))
                n += 1
    print('segments set to %.2f mm: %d' % (W50, n))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
sys.stdout.flush()
os._exit(0)
