"""Project library for the r3.0 study: symbols (MMDVM_r30.kicad_sym) and footprints (MMDVM_r30.pretty)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symgen  # noqa: E402

RAK_PADS = {  # pad -> (name, type)   RAK4630 datasheet pin table, pin 1 = top-right, counter-clockwise
    1: ('VBUS', 'power_in'), 2: ('USB-', 'bidirectional'), 3: ('USB+', 'bidirectional'),
    4: ('P0.13', 'bidirectional'), 5: ('P0.14', 'bidirectional'), 6: ('P0.15', 'bidirectional'),
    7: ('P0.16', 'bidirectional'), 8: ('P0.17', 'bidirectional'), 9: ('P0.19', 'bidirectional'),
    10: ('P0.20', 'bidirectional'), 11: ('P0.21', 'bidirectional'), 12: ('P0.10/NFC2', 'bidirectional'),
    13: ('P0.09/NFC1', 'bidirectional'), 14: ('GND', 'power_in'), 15: ('RF_BT', 'passive'), 16: ('GND', 'power_in'),
    17: ('NRF_RESET', 'input'), 18: ('SWDCLK', 'input'), 19: ('SWDIO', 'bidirectional'),
    20: ('VBAT_SX', 'power_in'), 21: ('VBAT_IO_SX', 'power_in'), 22: ('GND', 'power_in'),
    23: ('P0.24', 'bidirectional'), 24: ('P0.25', 'bidirectional'), 25: ('P1.01', 'bidirectional'),
    26: ('P1.02', 'bidirectional'), 27: ('P1.03', 'bidirectional'), 28: ('P1.04', 'bidirectional'),
    29: ('P0.03/QSPI', 'bidirectional'), 30: ('P0.02/QSPI', 'bidirectional'), 31: ('P0.28/QSPI', 'bidirectional'),
    32: ('P0.29/QSPI', 'bidirectional'), 33: ('P0.30/QSPI', 'bidirectional'), 34: ('P0.26/QSPI', 'bidirectional'),
    35: ('GND', 'power_in'), 36: ('GND', 'power_in'), 37: ('RF_LORA', 'passive'), 38: ('GND', 'power_in'),
    39: ('P0.31/AIN7', 'bidirectional'), 40: ('P0.05/AIN3', 'bidirectional'), 41: ('P0.04/AIN2', 'bidirectional'),
    42: ('GND', 'power_in'), 43: ('VDD_NRF', 'passive'), 44: ('VBAT_NRF', 'power_in'),
}
LEFT = [44, 43, 20, 21, 1, 2, 3, 17, 18, 19, 15, 37, 14, 16, 22, 35, 36, 38, 42]


def rak4630_symbol():
    pins = []
    for n in LEFT:
        nm, t = RAK_PADS[n]
        pins.append((str(n), nm, t, 'L'))
    for n in sorted(RAK_PADS):
        if n not in LEFT:
            nm, t = RAK_PADS[n]
            pins.append((str(n), nm, t, 'R'))
    return symgen.symbol('RAK4630', 'U', pins, footprint='MMDVM_r30:RAK4630',
                         datasheet='https://docs.rakwireless.com/product-categories/wisduo/rak4630-module/datasheet/',
                         description='RAKwireless RAK4630 stamp module, nRF52840 + SX1262 (use -SM-NI for RF pads)')


def max17048_symbol():
    # pinout per MAX17048 TDFN-8 (CTG, CELL, VDD, GND, ALRT, QSTRT, SCL, SDA) + EP; VERIFY against datasheet
    pins = [('3', 'VDD', 'power_in', 'L'), ('2', 'CELL', 'input', 'L'), ('1', 'CTG', 'input', 'L'),
            ('6', 'QSTRT', 'input', 'L'), ('4', 'GND', 'power_in', 'L'), ('9', 'EP', 'passive', 'L'),
            ('8', 'SDA', 'bidirectional', 'R'), ('7', 'SCL', 'input', 'R'), ('5', '~{ALRT}', 'open_collector', 'R')]
    return symgen.symbol('MAX17048', 'U', pins, footprint='Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.6mm',
                         datasheet='https://www.analog.com/en/products/max17048.html',
                         description='1-cell ModelGauge fuel gauge, I2C 0x36')


# ------------------------------------------------------------------------------ footprints
def rak4630_footprint():
    """Land pattern from the RAK4630 datasheet (pcb_footprint / mechanical drawing), origin = module centre.

    Pads 0.9 x 1.3 mm, 0.52 mm outside the module edge, pitch 1.2 mm. Module 23 x 15 mm.
    """
    W, H = 23.0, 15.0
    pw, pl, out = 0.9, 1.3, 0.52
    c = pl / 2 - out          # pad centre inside the edge
    pads = {}
    for k in range(13):       # top row, pin 1 at the right
        pads[1 + k] = (19.70 - 1.2 * k, c, pw, pl)
    left_y = [2.09, 3.29] + [5.69 + 1.2 * i for i in range(7)]
    for i, y in enumerate(left_y):          # pins 14..22 top -> bottom
        pads[14 + i] = (c, y, pl, pw)
    for k in range(13):       # bottom row, pins 23..35 left -> right
        pads[23 + k] = (2.80 + 1.2 * k, H - c, pw, pl)
    right_y = [12.95, 11.75] + [9.35 - 1.2 * i for i in range(7)]
    for i, y in enumerate(right_y):         # pins 36..44 bottom -> top
        pads[36 + i] = (W - c, y, pl, pw)
    lines = ['(footprint "RAK4630"', '\t(version 20260206)', '\t(generator "customlib")', '\t(layer "F.Cu")',
             '\t(descr "RAKwireless RAK4630 stamp module, 44 castellated pads 1.2 mm pitch, 23x15 mm. '
             'VERIFY against the RAK datasheet before fabrication")',
             '\t(attr smd)']
    lines.append('\t(property "Reference" "REF**" (at 0 -9.2 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    lines.append('\t(property "Value" "RAK4630" (at 0 9.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    hw, hh = W / 2, H / 2
    for (x1, y1, x2, y2) in ((-hw, -hh, hw, -hh), (hw, -hh, hw, hh), (hw, hh, -hw, hh), (-hw, hh, -hw, -hh)):
        lines.append(f'\t(fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width 0.1) (type solid)) (layer "F.Fab"))')
    cy = 0.25
    for (x1, y1, x2, y2) in ((-hw - out - cy, -hh - out - cy, hw + out + cy, -hh - out - cy),
                             (hw + out + cy, -hh - out - cy, hw + out + cy, hh + out + cy),
                             (hw + out + cy, hh + out + cy, -hw - out - cy, hh + out + cy),
                             (-hw - out - cy, hh + out + cy, -hw - out - cy, -hh - out - cy)):
        lines.append(f'\t(fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    # pin-1 marker
    lines.append(f'\t(fp_circle (center {19.70 - hw:.3f} {-hh - out - 0.6:.3f}) (end {19.70 - hw + 0.2:.3f} {-hh - out - 0.6:.3f}) '
                 '(stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    for n in sorted(pads):
        x, y, sx, sy = pads[n]
        lines.append(f'\t(pad "{n}" smd rect (at {x - hw:.3f} {y - hh:.3f}) (size {sx:.2f} {sy:.2f}) '
                     '(layers "F.Cu" "F.Mask" "F.Paste"))')
    lines.append(')')
    return '\n'.join(lines) + '\n'


def ls_mezzanine_footprint():
    """96Boards LS male header for the underside of a mezzanine.

    The stock 2x20 2.00 mm SMT header with odd/even pad numbers swapped, so that footprint pad n lands on
    baseboard LS pin n when the part is placed on B.Cu (rotation 270, origin = connector centre).
    """
    import re
    src = os.path.join(os.environ.get('KICAD_FOOTPRINT_DIR', r'C:/Program Files/KiCad/10.0/share/kicad/footprints'),
                       'Connector_PinHeader_2.00mm.pretty', 'PinHeader_2x20_P2.00mm_Vertical_SMD.kicad_mod')
    t = open(src, encoding='utf-8').read()
    t = t.replace('(footprint "PinHeader_2x20_P2.00mm_Vertical_SMD"',
                  '(footprint "LS_2x20_P2.00mm_SMD_MezzanineBottom"', 1)
    t = re.sub(r'\(descr "[^"]*"\)', '(descr "96Boards LS 2x20 2.00 mm SMT male header for the mezzanine '
               'underside: odd/even pad numbers swapped so pad n = LS pin n on B.Cu, rotation 270")', t, count=1)

    def swap(m):
        n = int(m.group(1))
        return '(pad "%d"' % (n + 1 if n % 2 else n - 1)
    return re.sub(r'\(pad "(\d+)"', swap, t)


def write(libdir):
    os.makedirs(os.path.join(libdir, 'MMDVM_r30.pretty'), exist_ok=True)
    pmos = symgen.symbol('PMOS_SON8', 'Q', [('4', 'G', 'input', 'L'), ('1', 'S', 'passive', 'R'),
                                             ('2', 'S', 'passive', 'R'), ('3', 'S', 'passive', 'R'),
                                             ('5', 'D', 'passive', 'R')],
                         footprint='Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET',
                         description='P-channel MOSFET, SON-8 3.3x3.3 (S=1,2,3 G=4 D=5), e.g. CSD25404Q3')
    syms = [rak4630_symbol(), max17048_symbol(), pmos]
    try:
        import tps61178
        syms.append(tps61178.symbol())
        open(os.path.join(libdir, 'MMDVM_r30.pretty', 'TPS61178_RNW.kicad_mod'), 'w', encoding='utf-8',
             newline='\n').write(tps61178.footprint())
    except ImportError:
        pass
    symgen.write_lib(os.path.join(libdir, 'MMDVM_r30.kicad_sym'), syms)
    open(os.path.join(libdir, 'MMDVM_r30.pretty', 'RAK4630.kicad_mod'), 'w', encoding='utf-8',
         newline='\n').write(rak4630_footprint())
    open(os.path.join(libdir, 'MMDVM_r30.pretty', 'LS_2x20_P2.00mm_SMD_MezzanineBottom.kicad_mod'), 'w',
         encoding='utf-8', newline='\n').write(ls_mezzanine_footprint())
    return os.path.join(libdir, 'MMDVM_r30.kicad_sym')


if __name__ == '__main__':
    print(write(sys.argv[1]))
