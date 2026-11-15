"""Simplified 3D bodies for the footprints that have no model in the KiCad library (needs CadQuery).

These are plain envelope shapes sized from the footprints' fabrication outlines and the datasheet heights.
They are good for renders and enclosure clearance checks, not for mechanical detail.
Output: ../3dmodels/<name>.step, referenced from the board as ${KIPRJMOD}/3dmodels/<name>.step.

Usage: python models3d.py
"""
import os

import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '3dmodels')
BLACK = cq.Color(0.12, 0.12, 0.12)
SILVER = cq.Color(0.78, 0.78, 0.76)
IVORY = cq.Color(0.93, 0.91, 0.84)
WHITE = cq.Color(0.95, 0.95, 0.93)
BOARD = cq.Color(0.05, 0.15, 0.30)


def box(x0, y0, x1, y1, z0, z1):
    """Footprint coordinates (y down) -> model coordinates (y up)."""
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, -y1, z0))


def save(name, *parts):
    a = cq.Assembly()
    for i, (shape, colour) in enumerate(parts):
        a.add(shape, name='p%d' % i, color=colour)
    os.makedirs(OUT, exist_ok=True)
    a.save(os.path.join(OUT, name + '.step'))
    print('wrote', name)


def ic(name, x0, y0, x1, y1, h):
    save(name, (box(x0, y0, x1, y1, 0.02, h), BLACK))


# leadless ICs
ic('DFN-8-1EP_2x2mm_P0.5mm_EP0.9x1.3mm', -1.0, -1.0, 1.0, 1.0, 0.75)
ic('TDFN-12_2x3mm_P0.5mm', -1.0, -1.5, 1.0, 1.5, 0.75)
ic('Texas_RWU0007A_VQFN-7_2x2mm_P0.5mm', -1.0, -1.0, 1.0, 1.0, 0.9)
ic('TPS61178_RNW', -1.75, -1.5, 1.75, 1.5, 1.0)
# crystal, 5.0 x 3.2 x 1.1
save('Crystal_SMD_Abracon_ABM3-2Pin_5.0x3.2mm', (box(-2.5, -1.6, 2.5, 1.6, 0.0, 0.3), BLACK),
     (box(-2.3, -1.4, 2.3, 1.4, 0.3, 1.1), SILVER))
# Littelfuse NANO2 451/453: 6.1 x 2.69 x 2.69, metal end caps
save('Fuse_Littelfuse-NANO2-451_453', (box(-1.8, -1.3, 1.8, 1.3, 0.05, 2.65), WHITE),
     (box(-3.05, -1.345, -1.8, 1.345, 0.0, 2.69), SILVER), (box(1.8, -1.345, 3.05, 1.345, 0.0, 2.69), SILVER))
# JST PH side-entry SMT header, 3 way
save('JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal',
     (box(-4.95, -1.6, 4.95, 4.4, 0.0, 4.8).cut(box(-3.0, 1.0, 3.0, 4.5, 0.8, 4.0)), IVORY),
     (box(-2.25, -3.2, -1.75, -1.6, 0.0, 0.3), SILVER), (box(-0.25, -3.2, 0.25, -1.6, 0.0, 0.3), SILVER),
     (box(1.75, -3.2, 2.25, -1.6, 0.0, 0.3), SILVER))
# Alps SKRTLAE010 side push switch: 4.5 x 3.4 x 3.3 mm (W x D x H, Alps product page), round 2 mm stem at
# mid height pointing towards +y, tip 2.05 mm from the guide bosses
save('SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010', (box(-2.25, -1.5, 2.25, 1.46, 0.0, 3.3), SILVER),
     (cq.Workplane('XZ').center(0, 1.65).circle(1.0).extrude(0.6).translate((0, -1.46, 0)), BLACK))
# u-blox MAX form factor: 9.7 x 10.1 x 2.5, shielded
save('ublox_MAX', (box(-4.85, -5.05, 4.85, 5.05, 0.0, 0.6), BOARD), (box(-4.4, -4.6, 4.4, 4.6, 0.6, 2.5), SILVER))
# RAK4630: 23 x 15 x 3.0 (footprint long axis = x), shield over most of the module
save('RAK4630', (box(-11.5, -7.5, 11.5, 7.5, 0.0, 0.8), BOARD), (box(-10.3, -6.6, 8.5, 6.6, 0.8, 3.0), SILVER))
