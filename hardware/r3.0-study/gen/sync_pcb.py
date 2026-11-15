"""Update footprint links (symbol path, value, fields) of the existing main PCB from the schematic by reference.

Use after regenerating the schematic (new symbol UUIDs) so the routed board stays in sync without re-placing.
"""
import os
import sys

import pcbnew

import main_pcb

comps, pins = main_pcb.netlist()
PCB = os.path.join(main_pcb.PRJ, 'mmdvm_mesh.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
bad = 0
for fp in board.GetFootprints():
    ref = fp.GetReference()
    c = comps.get(ref)
    if not c:
        continue
    # pads first: after removing fields the binding sometimes hands out a broken pad list
    for pad in fp.Pads():
        n = pins.get((ref, pad.GetNumber()))
        if n and pad.GetNetname() != n:
            bad += 1
            print('net differs', ref, pad.GetNumber(), pad.GetNetname(), '!=', n)
    fp.SetPath(pcbnew.KIID_PATH(c['path']))
    fp.SetValue(c['val'])
    if fp.GetFPIDAsString() != c['fp']:
        bad += 1
        print('footprint differs', ref, fp.GetFPIDAsString(), '!=', c['fp'])
    for f in list(fp.GetFields()):
        if not f.IsMandatory():
            fp.Remove(f)
    for k, v in c['fields'].items():
        f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
        f.SetText(v); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
        f.SetOrdinal(fp.GetNextFieldOrdinal())
        fp.Add(f)
board.Save(PCB)
print('synced', len(comps), 'symbols; differences', bad)
sys.stdout.flush()
os._exit(0)
