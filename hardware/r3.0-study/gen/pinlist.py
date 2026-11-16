import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402

L = kisch.KICAD_SYM
_cache = {}


def findlib(name):
    for f in glob.glob(L + '/*.kicad_sym'):
        if f not in _cache:
            _cache[f] = open(f, encoding='utf-8').read()
        if ('(symbol "%s"' % name) in _cache[f]:
            return os.path.basename(f)[:-len('.kicad_sym')]
    return None


ids = []
for a in sys.argv[1:]:
    if ':' in a:
        ids.append(a)
    else:
        lib = findlib(a)
        print('found', a, '->', lib)
        if lib:
            ids.append(lib + ':' + a)
for i in ids:
    try:
        s = kisch.lib_symbol(i)
    except Exception as e:  # noqa: BLE001
        print('ERR', i, e)
        continue
    pins = kisch.symbol_pins(s)
    fp = [p for p in kisch.find(s, 'property') if p[1] == 'Footprint']
    print(f"\n{i}  fp={fp[0][2] if fp else ''}  units={kisch.symbol_units(s)}")
    print('  ' + ' '.join(f"{n}:{nm}({t[:3]})" for (u, n, nm, t, x, y, a) in
                          sorted(pins, key=lambda p: (p[0], len(p[1]), p[1]))))
