"""Remove the items a DRC report lists as track_dangling / via_dangling (run with KiCad's python).

For the leftovers fix_dangling.py does not catch (chains of stubs that end on nothing). The caller must
re-run DRC afterwards and confirm that nothing became unconnected; restore the board if it did.

Usage: python drop_dangling.py <drc.json>
"""
import json
import os
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
d = json.load(open(sys.argv[1], encoding='utf-8'))
want = {i['uuid'] for x in d['violations'] if x['type'] in ('via_dangling', 'track_dangling') for i in x['items']}
kill = [t for t in board.GetTracks() if t.m_Uuid.AsString() in want and not t.IsLocked()]
for t in kill:
    board.Remove(t)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print('removed', len(kill), 'of', len(want))
sys.stdout.flush()
os._exit(0)
