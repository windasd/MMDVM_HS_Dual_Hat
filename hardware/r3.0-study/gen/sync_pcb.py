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
# all pads first, in their own pass: once fields have been removed the binding hands out broken pad lists
for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        n = pins.get((ref, pad.GetNumber()))
        if n and pad.GetNetname() != n:
            bad += 1
            print('net differs', ref, pad.GetNumber(), pad.GetNetname(), '!=', n)
for fp in list(board.GetFootprints()):
    ref = fp.GetReference()
    c = comps.get(ref)
    if not c:
        continue
    fp.SetPath(pcbnew.KIID_PATH(c['path']))
    fp.SetValue(c['val'])
    if fp.GetFPIDAsString() != c['fp']:
        bad += 1
        print('footprint differs', ref, fp.GetFPIDAsString(), '!=', c['fp'])
    # update in place (removing fields breaks the python proxies of the footprints that follow)
    have = {f.GetName(): f for f in fp.GetFields() if not f.IsMandatory()}
    for k, v in c['fields'].items():
        if k in have:
            if have[k].GetText() != v:
                have[k].SetText(v)
        else:
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
            f.SetText(v); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
            f.SetOrdinal(fp.GetNextFieldOrdinal())
            fp.Add(f)
    for k in have:
        if k not in c['fields']:
            have[k].SetText('')
board.Save(PCB)
print('synced', len(comps), 'symbols; differences', bad)
sys.stdout.flush()
os._exit(0)
