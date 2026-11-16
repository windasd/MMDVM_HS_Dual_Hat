"""Generate simple rectangular KiCad 10 symbols (pins left/right/top/bottom) into a .kicad_sym library."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisch import Q, dump, fmt  # noqa: E402

G = 2.54


def _prop(name, val, x, y, hide=False, justify=None):
    p = ['property', Q(name), Q(val), ['at', fmt(x), fmt(y), '0']]
    if hide:
        p.append(['hide', 'yes'])
    eff = ['effects', ['font', ['size', '1.27', '1.27']]]
    if justify:
        eff.append(['justify', justify])
    p.append(eff)
    return p


def symbol(name, ref, pins, footprint='', datasheet='', description='', value=None):
    """pins: list of (number, name, etype, side) with side in L R T B; order = list order per side."""
    sides = {s: [p for p in pins if p[3] == s] for s in 'LRTB'}
    nmax = max(len(sides['L']), len(sides['R']), 1)
    tmax = max(len(sides['T']), len(sides['B']), 0)
    name_w = max([len(p[1]) for p in pins] + [4]) * 1.27 * 0.8
    w = max(2 * name_w + 4 * G, (tmax + 1) * G * 2)
    w = round(w / (2 * G) + 0.49) * 2 * G
    h = round(((nmax + 1) * G) / (2 * G) + 0.49) * 2 * G
    x0, x1, y0, y1 = -w / 2, w / 2, -h / 2, h / 2
    gr = [['rectangle', ['start', fmt(x0), fmt(y1)], ['end', fmt(x1), fmt(y0)],
           ['stroke', ['width', '0.254'], ['type', 'default']], ['fill', ['type', 'background']]]]
    pl = []
    L = 2 * G

    def pin(num, nm, et, x, y, ang):
        hidden = et.endswith('_hidden')
        et = et.replace('_hidden', '')
        pp = ['pin', et, 'line', ['at', fmt(x), fmt(y), str(ang)], ['length', fmt(L)]]
        if hidden:
            pp.append(['hide', 'yes'])
        pp += [['name', Q(nm), ['effects', ['font', ['size', '1.27', '1.27']]]],
               ['number', Q(num), ['effects', ['font', ['size', '1.27', '1.27']]]]]
        pl.append(pp)

    for i, (num, nm, et, s) in enumerate(sides['L']):
        pin(num, nm, et, x0 - L, y1 - G * (i + 1), 0)
    for i, (num, nm, et, s) in enumerate(sides['R']):
        pin(num, nm, et, x1 + L, y1 - G * (i + 1), 180)
    for i, (num, nm, et, s) in enumerate(sides['T']):
        pin(num, nm, et, x0 + G * 2 * (i + 1), y1 + L, 270)
    for i, (num, nm, et, s) in enumerate(sides['B']):
        pin(num, nm, et, x0 + G * 2 * (i + 1), y0 - L, 90)
    # snap pins to the 1.27 grid
    s = ['symbol', Q(name), ['pin_names', ['offset', '0.508']], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
         ['on_board', 'yes'],
         _prop('Reference', ref, x0, y1 + 1.27, justify='left'),
         _prop('Value', value or name, x0, y0 - 1.27 - (L if sides['B'] else 0), justify='left'),
         _prop('Footprint', footprint, 0, 0, hide=True),
         _prop('Datasheet', datasheet, 0, 0, hide=True),
         _prop('Description', description, 0, 0, hide=True),
         ['symbol', Q(name + '_0_1')] + gr,
         ['symbol', Q(name + '_1_1')] + pl,
         ['embedded_fonts', 'no']]
    return s


def write_lib(path, syms):
    lib = ['kicad_symbol_lib', ['version', '20251024'], ['generator', Q('symgen')],
           ['generator_version', Q('10.0')]] + syms
    open(path, 'w', encoding='utf-8', newline='\n').write(dump(lib) + '\n')
