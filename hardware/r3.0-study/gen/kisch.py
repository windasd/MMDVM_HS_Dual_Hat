"""Minimal KiCad 10 schematic generator (label-based) used for the r3.0 study board.

A sheet is described as a list of parts, each with a pin -> net map. The generator places the
parts on a grid, draws a short stub from every pin, and terminates it with a power symbol
(power nets), a global label (nets used on several sheets), a local label, or a no-connect flag.
kicad-cli then re-saves the file in canonical form, and the exported netlist is compared with
the specification pin by pin.
"""
import os
import re
import uuid as _uuid

KICAD_SYM = os.environ.get("KICAD_SYMBOL_DIR", r"C:/Program Files/KiCad/10.0/share/kicad/symbols")


# ----------------------------------------------------------------------------- s-expressions
class Q(str):
    """A quoted string atom."""


def tokenize(t):
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c in ' \t\r\n':
            i += 1
        elif c in '()':
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while t[j] != '"':
                if t[j] == '\\':
                    buf.append(t[j:j + 2])
                    j += 2
                else:
                    buf.append(t[j])
                    j += 1
            yield Q(''.join(buf))
            i = j + 1
        else:
            j = i
            while j < n and t[j] not in ' \t\r\n()"':
                j += 1
            yield t[i:j]
            i = j


def parse(t):
    stack = [[]]
    for tok in tokenize(t):
        if tok == '(':
            stack.append([])
        elif tok == ')':
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(tok)
    return stack[0][0]


def dump(x, ind=0):
    if isinstance(x, list):
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return '(' + ' '.join(dump(e) for e in x) + ')'
        out = '(' + ' '.join(dump(e) for e in x if not isinstance(e, list))
        for e in x:
            if isinstance(e, list):
                out += '\n' + '\t' * (ind + 1) + dump(e, ind + 1)
        return out + '\n' + '\t' * ind + ')'
    if isinstance(x, Q):
        return '"' + x + '"'   # escapes were kept verbatim by the tokenizer
    return str(x)


def find(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None


def uid():
    return Q(str(_uuid.uuid4()))


def fmt(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') if isinstance(v, float) else str(v)


# ----------------------------------------------------------------------------- libraries
_libs = {}
_extra_libs = {}   # nickname -> path of project libraries


def lib_tree(nick):
    if nick not in _libs:
        path = _extra_libs.get(nick) or os.path.join(KICAD_SYM, nick + '.kicad_sym')
        _libs[nick] = parse(open(path, encoding='utf-8').read())
    return _libs[nick]


def lib_symbol(lib_id):
    """Return a flattened copy of a library symbol, renamed to the full lib_id."""
    import copy
    nick, name = lib_id.split(':', 1)
    tree = lib_tree(nick)
    syms = {e[1]: e for e in find(tree, 'symbol')}
    s = copy.deepcopy(syms[name])
    ext = first(s, 'extends')
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        while first(parent, 'extends'):
            parent = copy.deepcopy(syms[first(parent, 'extends')[1]])
        props = find(s, 'property')
        body = [e for e in parent if not (isinstance(e, list) and e and e[0] == 'property')]
        pname = parent[1]
        for e in body:
            if isinstance(e, list) and e and e[0] == 'symbol':
                e[1] = Q(name + e[1][len(pname):])
        # child properties replace the parent's; keep the parent's non-property flags
        s = [body[0], Q(name)] + [e for e in body[2:] if not (isinstance(e, list) and e[0] == 'symbol')] \
            + props + [e for e in body if isinstance(e, list) and e and e[0] == 'symbol']
    s[1] = Q(lib_id)
    return s


def symbol_pins(sym):
    """[(unit, number, name, type, x, y, angle)] for body style 1 (and common units 0)."""
    pins = []
    for sub in find(sym, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', sub[1])
        unit, style = int(m.group(1)), int(m.group(2))
        if style not in (0, 1):
            continue
        for p in find(sub, 'pin'):
            at = first(p, 'at')
            pins.append((unit, str(first(p, 'number')[1]), str(first(p, 'name')[1]), p[1],
                         float(at[1]), float(at[2]), int(float(at[3]) if len(at) > 3 else 0)))
    return pins


def symbol_units(sym):
    us = sorted({u for (u, *_r) in symbol_pins(sym)} - {0})
    return us or [1]


# ----------------------------------------------------------------------------- sheet builder
G = 2.54
OUT = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> outward screen direction


class Sheet:
    def __init__(self, name, filename, title, global_nets, power_nets, project, root_uuid, sheet_uuid,
                 paper='A3', cols_mm=380.0, ref_prefix=''):
        self.name, self.filename, self.title = name, filename, title
        self.global_nets, self.power_nets = global_nets, power_nets
        self.project, self.root_uuid, self.sheet_uuid = project, root_uuid, sheet_uuid
        self.paper, self.cols_mm = paper, cols_mm
        self.items, self.libsyms = [], {}
        self.x, self.y, self.row_h = 20 * G, 20 * G, 0.0
        self.pwr_n = 0
        self.ref_prefix = ref_prefix
        self.texts = []

    # -- helpers -------------------------------------------------------------
    def path(self):
        return '/' + self.root_uuid + ('/' + self.sheet_uuid if self.sheet_uuid else '')

    def _use(self, lib_id):
        if lib_id not in self.libsyms:
            self.libsyms[lib_id] = lib_symbol(lib_id)
        return self.libsyms[lib_id]

    @staticmethod
    def _prop(name, value, x, y, hide=False, angle=0, justify=None):
        eff = ['effects', ['font', ['size', '1.27', '1.27']]]
        if justify:
            eff.append(['justify', justify])
        p = ['property', Q(name), Q(value), ['at', fmt(x), fmt(y), str(angle)]]
        if hide:
            p.append(['hide', 'yes'])
        p.append(eff)
        return p

    def _symbol(self, lib_id, ref, value, x, y, unit=1, angle=0, footprint='', fields=None, in_bom=True,
                on_board=True, ref_xy=None, val_xy=None, hide_ref=False, hide_val=False, dnp=False):
        self._use(lib_id)
        s = ['symbol', ['lib_id', Q(lib_id)], ['at', fmt(x), fmt(y), str(angle)], ['unit', str(unit)],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'],
             ['on_board', 'yes' if on_board else 'no'], ['dnp', 'yes' if dnp else 'no'], ['uuid', uid()]]
        rx, ry = ref_xy or (x, y - 2 * G)
        vx, vy = val_xy or (x, y + 2 * G)
        s.append(self._prop('Reference', ref, rx, ry, hide=hide_ref))
        s.append(self._prop('Value', value, vx, vy, hide=hide_val))
        s.append(self._prop('Footprint', footprint, x, y, hide=True))
        s.append(self._prop('Datasheet', '', x, y, hide=True))
        for k, v in (fields or {}).items():
            s.append(self._prop(k, v, x, y, hide=True))
        s.append(['instances', ['project', Q(self.project), ['path', Q(self.path()), ['reference', Q(ref)],
                                                                ['unit', str(unit)]]]])
        self.items.append(s)
        return s

    def _wire(self, x1, y1, x2, y2):
        self.items.append(['wire', ['pts', ['xy', fmt(x1), fmt(y1)], ['xy', fmt(x2), fmt(y2)]],
                           ['stroke', ['width', '0'], ['type', 'default']], ['uuid', uid()]])

    def _label(self, net, x, y, d):
        ang = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}[d]
        just = 'left' if ang in (0, 90) else 'right'
        if net in self.global_nets:
            self.items.append(['global_label', Q(net), ['shape', 'bidirectional'], ['at', fmt(x), fmt(y), str(ang)],
                               ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just]], ['uuid', uid()]])
        else:
            self.items.append(['label', Q(net), ['at', fmt(x), fmt(y), str(ang)],
                               ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just, 'bottom']],
                               ['uuid', uid()]])

    def _power(self, net, x, y, d):
        self.pwr_n += 1
        gnd = net.upper().startswith('GND') or net.upper() in ('VSS', 'PACK-', 'CELL-')
        lib = 'power:GND' if gnd else 'power:VCC'
        # angle so that the symbol body points away from the pin (screen coordinates, CCW)
        if gnd:
            ang = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        else:
            ang = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        tx, ty = x + 3 * G * d[0], y + 3 * G * d[1]
        self._symbol(lib, '#PWR%s%03d' % (self.ref_prefix, self.pwr_n), net, x, y, angle=ang,
                     in_bom=False, on_board=False, ref_xy=(x, y), val_xy=(tx, ty), hide_ref=True)

    def _noconn(self, x, y):
        self.items.append(['no_connect', ['at', fmt(x), fmt(y)], ['uuid', uid()]])

    def text(self, s, x=None, y=None, size=2.0):
        self.texts.append((s, x, y, size))

    # -- placement -------------------------------------------------------------
    def newline(self, gap=8 * G):
        self.x = 20 * G
        self.y += self.row_h + gap
        self.row_h = 0.0

    def add(self, ref, lib_id, value, nets, footprint='', fields=None, dnp=False, in_bom=True, stub=3 * G):
        """Place every unit of a part; nets maps pin number -> net name or None (no connect)."""
        sym = self._use(lib_id)
        pins = symbol_pins(sym)
        units = symbol_units(sym)
        seen = set()
        for u in units:
            ups = [p for p in pins if p[0] in (0, u)]
            xs = [p[4] for p in ups] or [0.0]
            ys = [p[5] for p in ups] or [0.0]

            def lw(side):
                names = [nets.get(q[1]) or '' for q in ups if OUT[q[6] % 360][0] == side]
                names = [n for n in names if n and n not in self.power_nets]
                return (max([len(n) for n in names]) * 1.1 + 4.0) if names else 6 * G
            lw_l, lw_r = lw(-1), lw(1)
            w = (max(xs) - min(xs)) + 2 * stub + lw_l + lw_r
            h = (max(ys) - min(ys)) + 2 * (stub + 4 * G)
            if self.x + w > self.cols_mm:
                self.newline()
            ox = self.x + stub + lw_l - min(xs)
            oy = self.y + stub + 4 * G + max(ys)
            ox, oy = round(ox / G) * G, round(oy / G) * G
            self._symbol(lib_id, ref, value, ox, oy, unit=u, footprint=footprint, fields=fields, dnp=dnp,
                         in_bom=in_bom, ref_xy=(ox, oy - max(ys) - 2 * G), val_xy=(ox, oy - min(ys) + 2 * G))
            for (pu, num, name, typ, px, py, pang) in ups:
                if (pu, num) in seen and pu == 0:
                    continue
                seen.add((pu, num))
                if num not in nets:
                    raise KeyError(f'{ref}: pin {num} ({name}) not assigned')
                net = nets[num]
                sx, sy = ox + px, oy - py
                d = OUT[pang % 360]
                if net is None:
                    self._noconn(sx, sy)
                    continue
                ex, ey = sx + stub * d[0], sy + stub * d[1]
                self._wire(sx, sy, ex, ey)
                if net in self.power_nets:
                    self._power(net, ex, ey, d)
                else:
                    self._label(net, ex, ey, d)
            self.x += w + 2 * G
            self.row_h = max(self.row_h, h)
        extra = set(nets) - {p[1] for p in pins}
        if extra:
            raise KeyError(f'{ref}: unknown pins {sorted(extra)}')

    # -- output ----------------------------------------------------------------
    def write(self, path, page='1'):
        bottom = self.y + self.row_h + 10 * G
        for name, (pw, ph) in (('A3', (420, 297)), ('A2', (594, 420)), ('A1', (841, 594)), ('A0', (1189, 841))):
            if self.cols_mm + 20 <= pw and bottom <= ph:
                self.paper = name
                break
        else:
            self.paper = 'A0'
        root = ['kicad_sch', ['version', '20260306'], ['generator', Q('eeschema')], ['generator_version', Q('10.0')],
                ['uuid', Q(self.sheet_uuid or self.root_uuid)], ['paper', Q(self.paper)],
                ['title_block', ['title', Q(self.title)], ['date', Q('2026-11-14')], ['rev', Q('3.0-study')],
                 ['company', Q('MMDVM_HS_Dual_Hat r3.0 (Meshtastic/GPS/1S4P) study')]],
                ['lib_symbols'] + list(self.libsyms.values())]
        for (s, x, y, size) in self.texts:
            root.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', fmt(x if x is not None else 10 * G),
                                                                     fmt(y if y is not None else 8 * G), '0'],
                         ['effects', ['font', ['size', fmt(size), fmt(size)]], ['justify', 'left', 'bottom']],
                         ['uuid', uid()]])
        root += self.items
        if not self.sheet_uuid:
            root.append(['sheet_instances', ['path', Q('/'), ['page', Q(page)]]])
        root.append(['embedded_fonts', 'no'])
        open(path, 'w', encoding='utf-8', newline='\n').write(dump(root) + '\n')
