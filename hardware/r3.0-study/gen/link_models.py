"""Point the board's footprints at the project 3D models in ../3dmodels (run with KiCad's python).

For every <name>.step there (made by models3d.py): a footprint model path ending in <name>.step that points
into the KiCad library is redirected to ${KIPRJMOD}/3dmodels/, and a footprint called <name> without any
model gets one. Run again after the board is regenerated.

Manufacturer models are used instead where they have been fetched into ../3dmodels/vendor (git-ignored, see
fetch_vendor_models.sh); `--simple` switches those parts back to the simplified bodies.

Usage: python link_models.py [--simple]
"""
import os
import re
import sys

import pcbnew

import main_pcb as M

PCB = os.path.join(M.PRJ, 'mmdvm_mesh.kicad_pcb')
names = [f[:-5] for f in os.listdir(os.path.join(M.PRJ, '3dmodels')) if f.endswith('.step')]
s = open(PCB, 'rb').read().decode('utf-8')
n = 0
for nm in names:
    s, k = re.subn(r'\$\{KICAD\d+_3DMODEL_DIR\}/[A-Za-z0-9_]+\.3dshapes/' + re.escape(nm) + r'\.step',
                   lambda m: '${KIPRJMOD}/3dmodels/' + nm + '.step', s)
    n += k
open(PCB, 'wb').write(s.encode('utf-8'))
board = pcbnew.LoadBoard(PCB)
added = 0
# footprint name -> (simplified model, vendor file, offset mm, rotation deg) ; transforms found from the STEP geometry
VENDOR = {
    # RAKwireless: origin at a corner, thickness along +y -> lay flat and centre
    'RAK4630': ('RAK4630', '3D_RAK4630.stp', (-11.5, -7.5, 0.0), (-90.0, 0.0, 0.0)),
    # Alps: guide bosses at y = 1.0, body bottom at z = -1.65, stem along -y
    'SW_Push_Alps_SKRTLAE010_NarrowPad1': ('SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010', 'SKRTLA.STEP',
                                           (0.0, -1.0, 1.65), (0.0, 0.0, 0.0)),
}
simple = '--simple' in sys.argv
vend = 0
for fp in board.GetFootprints():
    nm = fp.GetFPID().GetUniStringLibItemName()
    if nm not in VENDOR:
        continue
    base, vfile, off, rot = VENDOR[nm]
    use_vendor = not simple and os.path.exists(os.path.join(M.PRJ, '3dmodels', 'vendor', vfile))
    fp.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Show = True
    if use_vendor:
        m.m_Filename = '${KIPRJMOD}/3dmodels/vendor/' + vfile
        m.m_Offset = pcbnew.VECTOR3D(*off)
        m.m_Rotation = pcbnew.VECTOR3D(*rot)
        vend += 1
    else:
        m.m_Filename = '${KIPRJMOD}/3dmodels/%s.step' % base
    fp.Add3DModel(m)
    added += 1
print('manufacturer models in use:', vend)
for fp in board.GetFootprints():
    nm = fp.GetFPID().GetUniStringLibItemName()
    if nm in names and not list(fp.Models()):
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = '${KIPRJMOD}/3dmodels/%s.step' % nm
        m.m_Show = True
        fp.Add3DModel(m)
        added += 1
if added:
    board.Save(PCB)
print('model paths redirected', n, '| models added', added)
sys.stdout.flush()
os._exit(0)
