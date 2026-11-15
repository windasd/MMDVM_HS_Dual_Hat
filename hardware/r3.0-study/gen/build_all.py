"""Regenerate the r3.0 study schematic (and project library) and verify it.

Part numbers come from bom_fields.json (ref -> MFR/MPN/Mouser/LCSC), applied to the generated sheets and
to the two sheets copied from r1.3 (their SPR/SPN Mouser fields are replaced by Mouser/LCSC).
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import customlib  # noqa: E402
import kisch  # noqa: E402
import r30_parts as rp  # noqa: E402
import r30_parts2 as rp2  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, '..'))
BOMF = os.path.join(HERE, 'bom_fields.json')
FIELDS = json.load(open(BOMF, encoding='utf-8')) if os.path.exists(BOMF) else {}
KEYS = ('MFR', 'MPN', 'Mouser', 'Mouser_MPN', 'LCSC')
os.makedirs(OUT, exist_ok=True)
symlib = customlib.write(OUT)
gen = [('MMDVM IO', 'mmdvm_io.kicad_sch', rp.mmdvm_io()),
       ('Host interface', 'host_if.kicad_sch', rp.host_if()),
       ('Power', 'power.kicad_sch', rp2.power()),
       ('Meshtastic', 'meshtastic.kicad_sch', rp2.meshtastic()),
       ('GPS', 'gps.kicad_sch', rp2.gps()),
       ('Ethernet', 'ethernet.kicad_sch', rp2.ethernet())]
for _name, _fn, parts in gen:
    for p in parts:
        f = FIELDS.get(p['ref'])
        if f:
            for k in KEYS:
                p['fields'][k] = f.get(k, '')


def set_bom_fields(t):
    """Copied r1.3 sheets: replace SPR/SPN by Mouser/LCSC (and refresh MFR/MPN) from bom_fields.json."""
    for e in t:
        if not (isinstance(e, list) and e and e[0] == 'symbol'):
            continue
        props = {p[1]: p for p in kisch.find(e, 'property')}
        f = FIELDS.get(str(props['Reference'][2]))
        if not f:
            continue
        for k in ('SPR', 'SPN'):
            if k in props:
                e.remove(props.pop(k))
        at = kisch.first(e, 'at')
        for k in KEYS:
            if k in props:
                props[k][2] = kisch.Q(f.get(k, ''))
            else:
                e.insert(len(e) - 1, ['property', kisch.Q(k), kisch.Q(f.get(k, '')), ['at', at[1], at[2], '0'],
                                      ['hide', 'yes'], ['effects', ['font', ['size', '1.27', '1.27']]]])
    return t


def rf_patch(t):
    flg = [e for e in t if isinstance(e, list) and e and e[0] == 'symbol' and
           [p for p in kisch.find(e, 'property') if p[1] == 'Reference'][0][2] == '#FLG003']
    if flg:
        fx, fy = (float(v) for v in kisch.first(flg[0], 'at')[1:3])

        def touches(w):
            pts = kisch.first(w, 'pts')
            return any(abs(float(q[1]) - fx) < 1e-3 and abs(float(q[2]) - fy) < 1e-3 for q in pts[1:])
        t[:] = [e for e in t if not (e in flg or (isinstance(e, list) and e and e[0] == 'wire' and touches(e)))]
    for e in t:
        if isinstance(e, list) and e and e[0] == 'symbol':
            props = {p[1]: p for p in kisch.find(e, 'property')}
            if props['Reference'][2] in ('P1', 'P2'):
                props['Footprint'][2] = kisch.Q('Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical')
                props['Value'][2] = kisch.Q('U.FL (433 %s)' % ('TX' if props['Reference'][2] == 'P1' else 'RX'))
    return set_bom_fields(t)


cop = [('MMDVM RF', 'mmdvm_rf.kicad_sch', build.R13 + '/mmdvm_hs_dual_hat.kicad_sch', rf_patch),
       ('MMDVM MCU', 'mmdvm_mcu.kicad_sch', build.R13 + '/STM32F103.kicad_sch', set_bom_fields)]
root = build.build(OUT, gen, cop, extra_libs={'MMDVM_r30': symlib})
open(os.path.join(OUT, 'sym-lib-table'), 'w').write(
    '(sym_lib_table\n  (version 7)\n'
    '  (lib (name "MMDVM")(type "KiCad")(uri "${KIPRJMOD}/../../libraries/mmdvm_hs_dual_hat.kicad_sym")(options "")(descr ""))\n'
    '  (lib (name "MMDVM_r30")(type "KiCad")(uri "${KIPRJMOD}/MMDVM_r30.kicad_sym")(options "")(descr ""))\n)\n')
open(os.path.join(OUT, 'fp-lib-table'), 'w').write(
    '(fp_lib_table\n  (version 7)\n'
    '  (lib (name "MMDVM")(type "KiCad")(uri "${KIPRJMOD}/../../libraries/mmdvm_hs_dual_hat.pretty")(options "")(descr ""))\n'
    '  (lib (name "MMDVM_r30")(type "KiCad")(uri "${KIPRJMOD}/MMDVM_r30.pretty")(options "")(descr ""))\n)\n')
viol, bad, got = build.verify(root, gen)
print('NETDIFF', bad, '| ERC', len(viol), '| BOM fields for', len(FIELDS), 'refs')
for k, n in Counter((v['severity'], v['type']) for p, v in viol).most_common():
    print(' ', n, k)
for p, v in viol:
    if v['type'] not in ('footprint_link_issues', 'lib_symbol_issues'):
        print('  -', v['severity'], v['type'], '|', [i['description'][:70] for i in v['items']][:3])
