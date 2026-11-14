"""Autoroute the placed main board with Freerouting (run with KiCad's python).

  python route.py export            -> ../route/mmdvm_mesh.dsn
  java -jar freerouting.jar -de ../route/mmdvm_mesh.dsn -do ../route/mmdvm_mesh.ses -mp 40
  python route.py import            -> tracks imported, zones refilled, board saved
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, '..'))
PCB = os.path.join(PRJ, 'mmdvm_mesh.kicad_pcb')
RT = os.path.join(PRJ, 'route')
os.makedirs(RT, exist_ok=True)
board = pcbnew.LoadBoard(PCB)
if sys.argv[1] == 'export':
    print('export', pcbnew.ExportSpecctraDSN(board, os.path.join(RT, 'mmdvm_mesh.dsn')))
else:
    n0 = len(board.GetTracks())
    print('import', pcbnew.ImportSpecctraSES(board, os.path.join(RT, 'mmdvm_mesh.ses')))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print('tracks', n0, '->', len(board.GetTracks()))
sys.stdout.flush()
os._exit(0)
