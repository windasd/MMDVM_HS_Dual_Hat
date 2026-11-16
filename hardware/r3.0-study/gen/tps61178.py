"""TPS61178 (RNW0013A, 13-pin VQFN-HR) symbol and footprint from TI datasheet SLVSDA7E p.3 / p.38-39."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symgen  # noqa: E402

PINS = [('12', 'VIN', 'power_in', 'L'), ('11', 'EN', 'input', 'L'), ('1', 'FREQ/SYNC', 'input', 'L'),
        ('3', 'ILIMIT', 'input', 'L'), ('4', 'COMP', 'output', 'L'), ('5', 'FB', 'input', 'L'),
        ('2', 'AGND', 'power_in', 'L'), ('6', 'PGND', 'power_in', 'L'),
        ('7', 'SW', 'power_out', 'R'), ('13', 'BST', 'passive', 'R'), ('8', 'VOUT', 'power_out', 'R'),
        ('9', 'DISDRV', 'output', 'R'), ('10', 'VCC', 'power_out', 'R')]


def symbol():
    return symgen.symbol('TPS61178', 'U', PINS, footprint='MMDVM_r30:TPS61178_RNW',
                         datasheet='https://www.ti.com/lit/ds/symlink/tps61178.pdf',
                         description='20 V / 10 A synchronous boost with load-disconnect gate driver, VQFN-HR 13')


def footprint():
    pads = []
    for i, y in enumerate((-1.0, -0.5, 0.0, 0.5, 1.0)):          # pins 1..5, left column, pin 1 top
        pads.append((str(i + 1), -1.60, y, 0.70, 0.25, None))
    for i, y in enumerate((1.0, 0.5, 0.0, -0.5, -1.0)):          # pins 9..13, right column, pin 9 bottom
        pads.append((str(i + 9), 1.60, y, 0.70, 0.25, None))
    for n, x in (('6', -0.55), ('7', 0.0), ('8', 0.55)):          # bar leads, solder-mask defined
        pads.append((n, x, 0.0, 0.35, 3.50, -0.05))
    L = ['(footprint "TPS61178_RNW"', '\t(version 20260206)', '\t(generator "customlib")', '\t(layer "F.Cu")',
         '\t(descr "TI RNW0013A VQFN-HR 13 (3.5 x 3.0 mm), land pattern per SLVSDA7E p.38, stencil p.39. '
         'VERIFY before fabrication")', '\t(attr smd)',
         '\t(property "Reference" "REF**" (at 0 -2.6 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '\t(property "Value" "TPS61178" (at 0 2.6 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))']
    for (x1, y1, x2, y2) in ((-1.75, -1.5, 1.75, -1.5), (1.75, -1.5, 1.75, 1.5), (1.75, 1.5, -1.75, 1.5),
                             (-1.75, 1.5, -1.75, -1.5)):
        L.append(f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.1) (type solid)) (layer "F.Fab"))')
    for (x1, y1, x2, y2) in ((-2.2, -2.0, 2.2, -2.0), (2.2, -2.0, 2.2, 2.0), (2.2, 2.0, -2.2, 2.0),
                             (-2.2, 2.0, -2.2, -2.0)):
        L.append(f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    L.append('\t(fp_circle (center -2.15 -1.3) (end -2.05 -1.3) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    for (n, x, y, sx, sy, mm) in pads:
        layers = '"F.Cu" "F.Mask" "F.Paste"' if mm is None else '"F.Cu" "F.Mask"'
        extra = f' (solder_mask_margin {mm})' if mm is not None else ''
        L.append(f'\t(pad "{n}" smd roundrect (at {x} {y}) (size {sx} {sy}) (layers {layers}) '
                 f'(roundrect_rratio 0.2){extra})')
    for x in (-0.55, 0.0, 0.55):                                   # 3 paste apertures per bar, 1.2 mm pitch
        for y in (-1.2, 0.0, 1.2):
            L.append(f'\t(pad "" smd rect (at {x} {y}) (size 0.25 1.0) (layers "F.Paste"))')
    L.append(')')
    return '\n'.join(L) + '\n'
