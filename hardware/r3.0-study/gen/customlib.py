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


LAN9500A_PINS = {  # LAN950x data sheet DS00001875E, table 3-9 (56-QFN); pad 57 = exposed pad (VSS)
    1: 'nPHY_INT', 2: 'TXN', 3: 'TXP', 4: 'VDD33A', 5: 'RXN', 6: 'RXP', 7: 'NC', 8: 'EXRES', 9: 'VDD33A',
    10: 'VDDPLL', 11: 'USBDM', 12: 'USBDP', 13: 'TEST2', 14: 'NC', 15: 'VDD33A', 16: 'USBRBIAS', 17: 'VDDUSBPLL',
    18: 'XI', 19: 'XO', 20: 'VBUS_DET', 21: 'VDDCORE', 22: 'MDC/GPIO2', 23: 'MDIO/GPIO1', 24: 'nRESET',
    25: 'VDD33IO', 26: 'nFDX_LED/GPIO8', 27: 'nLNKA_LED/GPIO9', 28: 'nSPD_LED/GPIO10', 29: 'EECLK/PWR_SEL',
    30: 'EECS', 31: 'EEDO/AUTOMDIX_EN', 32: 'EEDI', 33: 'TEST3', 34: 'PHY_SEL', 35: 'VDD33IO', 36: 'nTRST/RXD0',
    37: 'TDO/nPHY_RST', 38: 'TCK/RXD1', 39: 'TMS/RXD2', 40: 'TDI/RXD3', 41: 'RXCLK', 42: 'RXDV', 43: 'TXEN',
    44: 'RXER', 45: 'CRS/GPIO3', 46: 'COL/GPIO0', 47: 'TXCLK', 48: 'VDD33IO', 49: 'TEST1', 50: 'VDDCORE',
    51: 'VDD33IO', 52: 'VDD33IO', 53: 'TXD3/GPIO7/EEP_SIZE', 54: 'TXD2/GPIO6/PORT_SWAP',
    55: 'TXD1/GPIO5/RMT_WKP', 56: 'TXD0/GPIO4/EEP_DISABLE', 57: 'VSS',
}


def lan9500a_symbol():
    left = [11, 12, 16, 20, 24, 18, 19, 29, 34, 13, 33, 49, 25, 35, 48, 51, 52, 21, 50, 17, 10, 57]
    pins = [(str(n), LAN9500A_PINS[n], 'passive', 'L') for n in left]
    pins += [(str(n), LAN9500A_PINS[n], 'passive', 'R') for n in (3, 2, 6, 5, 4, 9, 15, 8, 27, 28, 26)]
    pins += [(str(n), LAN9500A_PINS[n], 'passive', 'R') for n in sorted(LAN9500A_PINS)
             if n not in left and n not in (3, 2, 6, 5, 4, 9, 15, 8, 27, 28, 26)]
    return symgen.symbol('LAN9500A', 'U', pins, footprint='Package_DFN_QFN:QFN-56-1EP_8x8mm_P0.5mm_EP5.6x5.6mm',
                         datasheet='https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/'
                                   'DataSheets/LAN950x-Data-Sheet-DS00001875.pdf',
                         description='USB 2.0 Hi-Speed to 10/100 Ethernet controller with PHY, 56-QFN')


# ------------------------------------------------------------------------------ footprints
def hs_connector_footprint():
    """96Boards high-speed connector (60 pin, 0.8 mm) for the mezzanine underside.

    Taken from https://github.com/LordRafa/96boards-kicad10-mezzanine-template (BSD 2-clause, see
    MMDVM_r30.pretty/HS_60P_LICENSE.txt), kept in vendor_fp/. Only the 3D model reference is dropped.
    """
    import re
    t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor_fp',
                          'AMPHENOL_61083-063402LF.kicad_mod'), encoding='utf-8').read()
    return re.sub(r'\n\t\(model .*?\n\t\)', '', t, flags=re.S)
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


def skrtlae010_footprint():
    """Alps SKRTLAE010 side push button with the two "1" pads narrowed.

    In the stock footprint those pads sit 0.0993 mm from the part's own locating holes, just under the 0.1 mm
    hole-clearance rule. Each pad is 0.05 mm narrower here (0.70 mm, outer edge pulled in), which gives 0.12 mm.
    """
    import re
    src = os.path.join(os.environ.get('KICAD_FOOTPRINT_DIR', r'C:/Program Files/KiCad/10.0/share/kicad/footprints'),
                       'Button_Switch_SMD.pretty', 'SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010.kicad_mod')
    t = open(src, encoding='utf-8').read()
    t = t.replace('(footprint "SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010"',
                  '(footprint "SW_Push_Alps_SKRTLAE010_NarrowPad1"', 1)
    t, n = re.subn(r'(\(pad "1" smd roundrect\s+\(at -?)1\.225( -0\.9\)\s+\(size )0\.75( 1\.8\))', r'\g<1>1.2\g<2>0.7\g<3>', t)
    assert n == 2, n
    return t


def silk_trimmed(lib, name, new_name, drop, note):
    """Stock footprint `lib:name` without the silkscreen shapes for which drop(x1, y1, x2, y2) is true."""
    import re
    src = os.path.join(os.environ.get('KICAD_FOOTPRINT_DIR', r'C:/Program Files/KiCad/10.0/share/kicad/footprints'),
                       lib + '.pretty', name + '.kicad_mod')
    t = open(src, encoding='utf-8').read()
    t = t.replace('(footprint "%s"' % name, '(footprint "%s"' % new_name, 1)
    t = re.sub(r'\(descr "([^"]*)"\)', lambda m: '(descr "%s; %s")' % (m.group(1), note), t, count=1)

    def shape(m):
        blk = m.group(0)
        if '(layer "F.SilkS")' not in blk:
            return blk
        x1, y1, x2, y2 = [float(v) for v in re.search(r'\(start (\S+) (\S+)\)\s+\(end (\S+) (\S+)\)', blk).groups()]
        return '' if drop(x1, y1, x2, y2) else blk
    return re.sub(r'\n\t\(fp_(?:line|rect)\n.*?\n\t\)', shape, t, flags=re.S)


def edge_variants():
    """Parts that hang over the board edge: silk beyond the edge is left out (DRC: silk clipped by board edge)."""
    return {
        # C&K PCM12 slide switch: lever outline (y > 1.8) lies outside the board
        'SW_SPDT_PCM12_EdgeMount': silk_trimmed(
            'Button_Switch_SMD', 'SW_SPDT_PCM12', 'SW_SPDT_PCM12_EdgeMount',
            lambda x1, y1, x2, y2: max(y1, y2) > 1.8, 'lever outline removed from silk for mounting at the board edge'),
        # right-angle console header: pin outlines (x > 4.2) cross the board edge
        'PinHeader_1x06_P2.54mm_Horizontal_EdgeMount': silk_trimmed(
            'Connector_PinHeader_2.54mm', 'PinHeader_1x06_P2.54mm_Horizontal',
            'PinHeader_1x06_P2.54mm_Horizontal_EdgeMount',
            lambda x1, y1, x2, y2: max(x1, x2) > 4.2, 'pin outlines removed from silk for mounting at the board edge'),
    }


def write(libdir):
    os.makedirs(os.path.join(libdir, 'MMDVM_r30.pretty'), exist_ok=True)
    for name, text in edge_variants().items():
        open(os.path.join(libdir, 'MMDVM_r30.pretty', name + '.kicad_mod'), 'w', encoding='utf-8',
             newline='\n').write(text)
    open(os.path.join(libdir, 'MMDVM_r30.pretty', 'SW_Push_Alps_SKRTLAE010_NarrowPad1.kicad_mod'), 'w',
         encoding='utf-8', newline='\n').write(skrtlae010_footprint())
    pmos = symgen.symbol('PMOS_SON8', 'Q', [('4', 'G', 'input', 'L'), ('1', 'S', 'passive', 'R'),
                                             ('2', 'S', 'passive', 'R'), ('3', 'S', 'passive', 'R'),
                                             ('5', 'D', 'passive', 'R')],
                         footprint='Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET',
                         description='P-channel MOSFET, SON-8 3.3x3.3 (S=1,2,3 G=4 D=5), e.g. CSD25404Q3')
    syms = [rak4630_symbol(), max17048_symbol(), pmos, lan9500a_symbol()]
    open(os.path.join(libdir, 'MMDVM_r30.pretty', 'AMPHENOL_61083-063402LF.kicad_mod'), 'w', encoding='utf-8',
         newline='\n').write(hs_connector_footprint())
    import shutil
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor_fp', 'HS_60P_LICENSE.txt'),
                os.path.join(libdir, 'MMDVM_r30.pretty', 'HS_60P_LICENSE.txt'))
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
