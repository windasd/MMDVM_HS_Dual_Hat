"""Build the r3.0 study schematic: generated sheets + copied r1.3 MMDVM sheets, then verify."""
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402
import r30_parts as rp  # noqa: E402

K = os.environ.get("KICAD_CLI", r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
PROJECT = 'mmdvm_mesh'
R13 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'r1.3')).replace(os.sep, '/')


def run(*a):
    r = subprocess.run([K, *a], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def build(out, generated, copied, extra_libs=None):
    """generated: [(sheet name, file, parts)], copied: [(sheet name, file, source path, patch fn)]."""
    os.makedirs(out, exist_ok=True)
    for nick, path in (extra_libs or {}).items():
        kisch._extra_libs[nick] = path
    root_uuid = str(uuid.uuid4())
    # nets per sheet -> global nets
    use = {}
    for name, fn, parts in generated:
        for prt in parts:
            for n in prt['nets'].values():
                if n:
                    use.setdefault(n, set()).add(fn)
    copied_globals = set()
    for name, fn, src, patch in copied:
        txt = open(src, encoding='utf-8').read()
        copied_globals |= set(re.findall(r'\(global_label "([^"]+)"', txt))
    global_nets = {n for n, s in use.items() if len(s) > 1 or n in copied_globals} - rp.POWER_NETS
    sheets = []
    for i, (name, fn, parts) in enumerate(generated):
        su = str(uuid.uuid4())
        n = len(parts)
        cols = 380.0 if n <= 45 else (560.0 if n <= 90 else 800.0)
        sh = kisch.Sheet(name, fn, name, global_nets, rp.POWER_NETS, PROJECT, root_uuid, su,
                         ref_prefix=str(i + 1), cols_mm=cols)
        for prt in parts:
            sh.add(prt['ref'], prt['lib'], prt['value'], prt['nets'], footprint=prt['fp'], fields=prt['fields'],
                   dnp=prt['dnp'], in_bom=prt['in_bom'])
        sh.write(os.path.join(out, fn))
        sheets.append((name, fn, su))
    for name, fn, src, patch in copied:
        su = str(uuid.uuid4())
        t = kisch.parse(open(src, encoding='utf-8').read())
        t = [e for e in t if not (isinstance(e, list) and e and e[0] in ('sheet', 'sheet_instances'))]
        for e in t:
            if isinstance(e, list) and e and e[0] == 'uuid':
                e[1] = kisch.Q(su)
            if isinstance(e, list) and e and e[0] == 'symbol':
                ref = [p for p in kisch.find(e, 'property') if p[1] == 'Reference'][0][2]
                unit = kisch.first(e, 'unit')[1]
                for inst in kisch.find(e, 'instances'):
                    e.remove(inst)
                e.append(['instances', ['project', kisch.Q(PROJECT), ['path', kisch.Q('/' + root_uuid + '/' + su),
                                                                        ['reference', kisch.Q(ref)],
                                                                        ['unit', unit]]]])
        if patch:
            t = patch(t)
        open(os.path.join(out, fn), 'w', encoding='utf-8', newline='\n').write(kisch.dump(t) + '\n')
        sheets.append((name, fn, su))
    # root sheet with one sheet symbol per sub-sheet
    root = ['kicad_sch', ['version', '20260306'], ['generator', kisch.Q('eeschema')],
            ['generator_version', kisch.Q('10.0')], ['uuid', kisch.Q(root_uuid)], ['paper', kisch.Q('A4')],
            ['title_block', ['title', kisch.Q('MMDVM + Meshtastic + GPS + 1S4P (r3.0 study)')],
             ['date', kisch.Q('2026-11-14')], ['rev', kisch.Q('3.0-study')]], ['lib_symbols']]
    for i, (name, fn, su) in enumerate(sheets):
        x, y = 25 + (i % 3) * 85, 40 + (i // 3) * 45
        root.append(['sheet', ['at', str(x), str(y)], ['size', '70', '25'], ['exclude_from_sim', 'no'],
                     ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'],
                     ['stroke', ['width', '0.1524'], ['type', 'solid']], ['fill', ['color', '0', '0', '0', '0.0']],
                     ['uuid', kisch.Q(su)],
                     ['property', kisch.Q('Sheetname'), kisch.Q(name), ['at', str(x), str(y - 0.7), '0'],
                      ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'bottom']]],
                     ['property', kisch.Q('Sheetfile'), kisch.Q(fn), ['at', str(x), str(y + 25.6), '0'],
                      ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'top']]],
                     ['instances', ['project', kisch.Q(PROJECT), ['path', kisch.Q('/' + root_uuid),
                                                                   ['page', kisch.Q(str(i + 2))]]]]])
    root.append(['sheet_instances', ['path', kisch.Q('/'), ['page', kisch.Q('1')]]])
    root.append(['embedded_fonts', 'no'])
    rootfile = os.path.join(out, PROJECT + '.kicad_sch')
    open(rootfile, 'w', encoding='utf-8', newline='\n').write(kisch.dump(root) + '\n')
    pro = os.path.join(out, PROJECT + '.kicad_pro')
    if not os.path.exists(pro):
        json.dump({"meta": {"filename": PROJECT + ".kicad_pro", "version": 3}}, open(pro, 'w'))
    return rootfile


def verify(rootfile, generated):
    out = os.path.dirname(rootfile)
    for fn in [f for f in os.listdir(out) if f.endswith('.kicad_sch')]:
        code, msg = run('sch', 'upgrade', '--force', os.path.join(out, fn))
        if code:
            print('UPGRADE FAIL', fn, msg)
    code, msg = run('sch', 'erc', '--severity-all', '--format', 'json', '-o', os.path.join(out, 'erc.json'), rootfile)
    erc = json.load(open(os.path.join(out, 'erc.json'), encoding='utf-8'))
    viol = [(s['path'], v) for s in erc['sheets'] for v in s['violations']]
    code, msg = run('sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', os.path.join(out, 'n.net'), rootfile)
    s = open(os.path.join(out, 'n.net'), encoding='utf-8').read()
    s = s[s.index('(nets'):]
    got = {}
    for blk in re.split(r'\n\t\t\(net\n', s)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1).split('/')[-1]
        for r_, p_ in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            got[(r_, p_)] = name
    bad = 0
    for name, fn, parts in generated:
        for prt in parts:
            if prt['ref'].startswith('#'):
                continue
            for pin, net in prt['nets'].items():
                g = got.get((prt['ref'], pin))
                want = net if net else None
                if want is None:
                    if g and not g.startswith('unconnected-'):
                        bad += 1
                        print('NETDIFF', prt['ref'], pin, 'want nc got', g)
                elif g != want:
                    bad += 1
                    print('NETDIFF', prt['ref'], pin, 'want', want, 'got', g)
    return viol, bad, got
