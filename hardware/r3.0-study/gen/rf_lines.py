"""Set the antenna feed lines to the 50 ohm width of the JLC04161H-7628 stack-up (run with KiCad's python).

The feeds run on F.Cu over the In1 ground plane (7628 prepreg, 0.2104 mm) with the F.Cu ground pour 0.25 mm
to either side, i.e. they are coplanar lines. The JLCPCB impedance calculator (checked 2026-11-16) gives for
50 ohm: 0.320 mm with a 10 mil (0.254 mm) gap, 0.349 mm with a 20 mil gap, 0.359 mm without coplanar ground.
The width is therefore 0.32 mm (0.35 mm with the 0.25 mm pour gap would be about 3 ohm low).

  python rf_lines.py --strip-gps   remove the GPS feed (autorouted through In2) so it can be re-routed on F.Cu
  python rf_lines.py               widen every F.Cu segment of the feed nets, refill zones
"""
import os
import sys

import pcbnew

import main_pcb as M

W50 = 0.32
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
