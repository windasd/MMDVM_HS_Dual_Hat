"""Concept enclosure / stack-up for the MMDVM + Meshtastic + GPS + 1S4P board.

Desk-standing version: the display faces the user, antennas point up from the top edge,
and a 30 mm fan in the top plenum exhausts the SoC "chimney".

This is a layout study, not a print-ready model. All dimensions are in mm.

Board coordinates (used for modelling, same as the 96Boards CE drawing):
  X = 0..85 along the Bubblegum-96 long edge; X = 85 (Wi-Fi antenna side) is the TOP when standing.
  Y = 0 is the USB/HDMI edge of the Bubblegum-96; the main board extends to +Y over the cells.
  Z = 0 is the Bubblegum-96 top copper; +Z points to the display (the FRONT when standing).
World coordinates (for previews): the board frame is rotated so +X points up, then tilted back.

Run with CadQuery 2.x:  python enclosure_concept.py [outdir]
Outputs: concept_assembly.step, enclosure_tub.stl, front_plate.stl, stand_cradle.stl, preview_*.png
"""
import math
import os
import sys

import cadquery as cq

# ---------------------------------------------------------------- parameters
P = dict(
    # Bubblegum-96 (96Boards CE v1.0/v2.0 2D reference drawing)
    sbc_w=85.0, sbc_d=54.0, sbc_t=1.6,
    sbc_holes=[(4.0, 18.5), (4.0, 50.0), (81.0, 18.5), (81.0, 50.0)],
    soc_heatsink=(25.0, 22.0, 40.0, 37.0, 6.0),   # x0, y0, x1, y1, height; SoC position TBC on the board
    mezz_gap=8.0,               # board-to-mezzanine spacing (CE spec v2.0)
    # main (mezzanine) board, extended towards +Y for the cells
    pcb_t=1.6, pcb_y1=-1.0, pcb_y2=145.5,
    mb_holes_ext=[(4.0, 142.5), (81.0, 142.5)],   # main-board holes beyond the last cell holder
    # 4x Keystone 1042P, mounted on the main-board underside, cells along X (vertical when standing)
    cell_len=77.1, cell_pitch=21.0, cell_h=20.5, cells_y0=55.5,
    # display: TJC8048X550_011R (resistive: 4-pin touch tail HST050008), TJC X5 datasheet p.7; long side along Y
    disp_w=136.9, disp_h=84.0, disp_pcb=1.6, disp_holes=(130.5, 77.6),
    lcd_w=120.7, lcd_h=75.8, lcd_t=4.5,         # front stack: 4.5 (R, this unit); 3.3 (N) / 5.08 (C)
    disp_back=6.0,                              # tallest part behind the PCB (XH connector)
    touch_gap=0.5,                              # keep the bezel off the touch film
    va_w=108.0, va_h=64.8, va_off=1.94,         # active area, offset away from the FPC edge
    # enclosure
    wall=2.5, back=2.5, front=2.5, clear=1.0,
    bottom_wall=7.0,            # thick bottom rail: carries two front-plate screw bosses outside the board stack
    top_parts=9.0,              # tallest part on the main-board top
    plenum=13.0,                # top air plenum (fan, SMA bodies, pigtails) beyond X = 85
    # fan: 30x30x10 mm 5 V, axis along X, exhausting up through the top wall
    fan=30.0, fan_t=10.0, fan_y=38.0, fan_holes=24.0,
    # antennas on the top wall: bulkhead SMA-female + IPEX pigtail (label, y, whip length; 0 = cable)
    # 433 TX and 433 RX at the two ends for the best duplex isolation.
    antennas=[("433 TX", 12.0, 195.0), ("GPS", 70.0, 0.0), ("LoRa 920", 100.0, 110.0), ("433 RX", 128.0, 195.0)],
    sma_hole=6.5, sma_flat=5.9,  # D-hole for 1/4"-36 bulkhead SMA (check the actual part)
    # desk stand
    tilt=12.0, foot_gap=8.0, stand_depth=55.0, cradle_w=12.0, cradle_y=(14.0, 118.0),
)


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def union_all(lst):
    u = lst[0]
    for o in lst[1:]:
        u = u.union(o)
    return u


def build(p=P):
    parts = {}
    # --- Bubblegum-96 with its tallest edge parts (approximate blocks)
    sbc = box(0, 0, -p["sbc_t"], p["sbc_w"], p["sbc_d"], 0)
    for (hx, hy) in p["sbc_holes"]:
        sbc = sbc.cut(cq.Workplane("XY").circle(1.25).extrude(5).translate((hx, hy, -3)))
    ports = (box(2, -1, 0, 14, 12, 1.6)              # microSD
             .union(box(17.5, -1, 0, 32.5, 11, 6.0))   # HDMI
             .union(box(38, -1, 0, 45, 5, 3.0))        # micro-USB 3.0
             .union(box(49.5, -2, 0, 63.7, 14, 7.0))   # USB host 2
             .union(box(69, -2, 0, 83, 14, 7.0))       # USB host 1
             .union(box(67, 40, 0, 76, 55, 6.5)))      # DC jack (not used)
    parts["bubblegum96"] = sbc.union(ports)
    hx0, hy0, hx1, hy1, hh = p["soc_heatsink"]
    fins = [box(hx0, hy0 + i * 2.5, 0.5, hx1, hy0 + i * 2.5 + 1.0, hh) for i in range(int((hy1 - hy0) / 2.5) + 1)]
    parts["soc_heatsink"] = box(hx0, hy0, 0.0, hx1, hy1, 1.5).union(union_all(fins))
    z_mb = p["mezz_gap"]
    z_mt = z_mb + p["pcb_t"]
    parts["ls_connector"] = box(10 - 2.5, 50 - 3.25, 0, 48 + 2.5, 50 + 3.25, z_mb)
    # --- main board
    mb = box(0, p["pcb_y1"], z_mb, p["sbc_w"], p["pcb_y2"], z_mt)
    for (hx, hy) in p["sbc_holes"] + p["mb_holes_ext"]:
        mb = mb.cut(cq.Workplane("XY").circle(1.35).extrude(5).translate((hx, hy, z_mb - 1)))
    parts["main_board"] = mb
    # side-panel controls on the +Y edge: USB-C, MESH button, power button, GPS switch, GPS LED
    parts["usb_c"] = box(30, p["pcb_y2"] - 7.5, z_mt, 39, p["pcb_y2"] + 1.0, z_mt + 3.3)
    parts["mesh_button"] = box(41, p["pcb_y2"] - 6, z_mt, 47, p["pcb_y2"] + 1.0, z_mt + 4)
    parts["power_button"] = box(50, p["pcb_y2"] - 6, z_mt, 56, p["pcb_y2"] + 1.0, z_mt + 4)
    parts["gps_switch"] = box(62, p["pcb_y2"] - 5, z_mt, 70.6, p["pcb_y2"] + 1.5, z_mt + 3.5)
    parts["gps_led"] = box(73.5, p["pcb_y2"] - 2, z_mt, 75.5, p["pcb_y2"], z_mt + 1)
    # layout zones on the main-board top (standing: X is height)
    parts["mmdvm_zone"] = box(5, 2, z_mt, 80, 52, z_mt + 3)          # over the Bubblegum (SoC column)
    parts["mesh_gps_zone"] = box(5, 60, z_mt, 42, 136, z_mt + 3)     # low in the cell column
    parts["power_zone"] = box(46, 60, z_mt, 82, 136, z_mt + 5)       # top of the cell column: heat rises away
    # --- cells under the extension (vertical when standing)
    cells = []
    x0 = (p["sbc_w"] - p["cell_len"]) / 2
    for i in range(4):
        y0 = p["cells_y0"] + i * p["cell_pitch"]
        holder = box(x0, y0, z_mb - 14.86, x0 + p["cell_len"], y0 + 20.7, z_mb)
        cell = (cq.Workplane("YZ").circle(9.3).extrude(65.0)
                .translate((x0 + 6.0, y0 + 10.35, z_mb - p["cell_h"] + 9.3)))
        cells.append(holder.union(cell))
    parts["cells_1s4p"] = union_all(cells)
    # --- enclosure: a tub (back + 4 walls) closed by a front plate carrying the display
    disp_t = p["disp_back"] + p["disp_pcb"] + p["lcd_t"] + p["touch_gap"]
    z_front_in = z_mt + p["top_parts"] + 2.0 + disp_t
    z_back_in = z_mb - p["cell_h"] - p["clear"]
    ix0 = -p["clear"]
    ix1 = p["sbc_w"] + p["clear"] + p["plenum"]
    iy0 = -2.0 - p["clear"]
    iy1 = p["pcb_y2"] + 1.0 + p["clear"]
    ox0, ox1, oy0, oy1 = ix0 - p["bottom_wall"], ix1 + p["wall"], iy0 - p["wall"], iy1 + p["wall"]
    z_out_back = z_back_in - p["back"]
    z_out_front = z_front_in + p["front"]
    cx, cy = (ix0 + ix1) / 2, (iy0 + iy1) / 2       # display centred on the front face
    # display: LCD stack against the front plate (touch gap), PCB behind it, XH connector at the -Y end
    z_lcd = z_front_in - p["touch_gap"]
    z_pcb = z_lcd - p["lcd_t"]
    lcd = box(cx - p["lcd_h"] / 2, cy - p["lcd_w"] / 2, z_pcb, cx + p["lcd_h"] / 2, cy + p["lcd_w"] / 2, z_lcd)
    dpcb = box(cx - p["disp_h"] / 2, cy - p["disp_w"] / 2, z_pcb - p["disp_pcb"],
               cx + p["disp_h"] / 2, cy + p["disp_w"] / 2, z_pcb)
    hx_, hy_ = p["disp_holes"][1] / 2, p["disp_holes"][0] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            dpcb = dpcb.cut(cq.Workplane("XY").circle(1.6).extrude(5).translate((cx + sx * hx_, cy + sy * hy_, z_pcb - 3)))
    xh_x0 = cx - p["disp_h"] / 2 + 3.2 + 31.24
    xh = box(xh_x0, cy - p["disp_w"] / 2, z_pcb - p["disp_pcb"] - p["disp_back"],
             xh_x0 + 15.12, cy - p["disp_w"] / 2 + 7.8, z_pcb - p["disp_pcb"])
    parts["display"] = lcd.union(dpcb).union(xh)
    tub = box(ox0, oy0, z_out_back, ox1, oy1, z_front_in).cut(box(ix0, iy0, z_back_in, ix1, iy1, z_front_in + 1))
    # corner posts for M3 heat-set inserts (front plate screws)
    posts, post_holes = [], []
    screw_pts = ((ix0 - p["bottom_wall"] / 2, iy0 + 6), (ix0 - p["bottom_wall"] / 2, iy1 - 6),
                 (ix1 - 4, iy0 + 4), (ix1 - 4, iy1 - 4))
    for (px, py) in screw_pts[2:]:
        posts.append(cq.Workplane("XY").circle(4.0).extrude(z_front_in - z_back_in).translate((px, py, z_back_in)))
    for (px, py) in screw_pts:
        post_holes.append(cq.Workplane("XY").circle(2.0).extrude(10).translate((px, py, z_front_in - 9.5)))
    tub = tub.union(union_all(posts)).cut(union_all(post_holes))
    # stand-offs from the back: Bubblegum-96 holes (to its underside) and main-board extension holes
    so = [cq.Workplane("XY").circle(3.0).circle(1.25).extrude(-p["sbc_t"] - z_back_in).translate((hx, hy, z_back_in))
          for (hx, hy) in p["sbc_holes"]]
    so += [cq.Workplane("XY").circle(3.0).circle(1.25).extrude(z_mb - z_back_in).translate((hx, hy, z_back_in))
           for (hx, hy) in p["mb_holes_ext"]]
    so += [cq.Workplane("XY").circle(2.5).circle(1.25).extrude(p["mezz_gap"]).translate((hx, hy, 0.0))
           for (hx, hy) in p["sbc_holes"]]
    parts["standoffs"] = union_all(so)
    front = box(ox0, oy0, z_front_in, ox1, oy1, z_out_front)
    vx = cx + p["va_off"]                          # active area is off-centre on the short axis
    front = front.cut(box(vx - p["va_h"] / 2 - 0.5, cy - p["va_w"] / 2 - 0.5, z_front_in - 1,
                          vx + p["va_h"] / 2 + 0.5, cy + p["va_w"] / 2 + 0.5, z_out_front + 1))
    # display bosses: M3 self-tapping / heat-set, hold the panel PCB with the touch gap
    bosses = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            bosses.append(cq.Workplane("XY").circle(3.5).circle(1.25).extrude(p["lcd_t"] + p["touch_gap"])
                          .translate((cx + sx * hx_, cy + sy * hy_, z_pcb)))
    front = front.union(union_all(bosses))
    for (px, py) in screw_pts:
        front = front.cut(cq.Workplane("XY").circle(1.7).extrude(10).translate((px, py, z_front_in - 1)))
    # side face (Y = 0): Bubblegum ports
    for (a, b, zt) in ((2, 14, 2.6), (17.5, 32.5, 7.0), (38, 45, 4.0), (49.5, 63.7, 8.0), (69, 83, 8.0)):
        tub = tub.cut(box(a - 0.5, oy0 - 1, -p["sbc_t"] - 0.5, b + 0.5, iy0 + 1, zt))
    # side face (+Y): USB-C, MESH button, power button, GPS switch, GPS LED
    for (a, b, zt) in ((29.5, 39.5, 3.8), (40.5, 47.5, 4.5), (49.5, 56.5, 4.5), (64.0, 68.6, 4.0)):
        tub = tub.cut(box(a, iy1 - 1, z_mt - 0.5, b, oy1 + 1, z_mt + zt))
    tub = tub.cut(cq.Workplane("XZ").center(74.5, z_mt + 2.2).circle(1.6).extrude(-10).translate((0, iy1 - 2, 0)))
    # --- top wall: fan exhaust grille, fan screws, bulkhead SMA D-holes, passive slots over the cell column
    z_mid = (z_back_in + z_front_in) / 2
    fan_c = (p["fan_y"], z_mid)
    grille = []
    for ring_r, n in ((0.0, 1), (5.5, 8), (10.5, 14)):
        for k in range(n):
            a = 2 * math.pi * k / n
            grille.append(cq.Workplane("YZ").circle(2.0).extrude(10)
                          .translate((ix1 - 3, fan_c[0] + ring_r * math.cos(a), fan_c[1] + ring_r * math.sin(a))))
    for sy in (-1, 1):
        for sz in (-1, 1):
            grille.append(cq.Workplane("YZ").circle(1.6).extrude(10).translate(
                (ix1 - 3, fan_c[0] + sy * p["fan_holes"] / 2, fan_c[1] + sz * p["fan_holes"] / 2)))
    tub = tub.cut(union_all(grille))
    parts["fan"] = (box(ix1 - p["fan_t"] - 0.5, fan_c[0] - p["fan"] / 2, fan_c[1] - p["fan"] / 2,
                        ix1 - 0.5, fan_c[0] + p["fan"] / 2, fan_c[1] + p["fan"] / 2)
                    .cut(cq.Workplane("YZ").circle(13.5).extrude(p["fan_t"] + 2)
                         .translate((ix1 - p["fan_t"] - 1.5, fan_c[0], fan_c[1])))
                    .union(cq.Workplane("YZ").circle(6.0).extrude(p["fan_t"])
                           .translate((ix1 - p["fan_t"] - 0.5, fan_c[0], fan_c[1]))))
    r = p["sma_hole"] / 2
    zc = z_mid
    ant_out, ant_in = [], []
    for (label, y, length) in p["antennas"]:
        hole = (cq.Workplane("YZ").circle(r).extrude(20).translate((ox1 - 10.0, y, zc))
                .cut(box(ox1 - 15, y - 5, zc - r + p["sma_flat"], ox1 + 15, y + 5, zc + 5)))
        tub = tub.cut(hole)
        ant_in.append(cq.Workplane("YZ").polygon(6, 8.0 / 0.866).extrude(8.0).translate((ix1 - 8.0, y, zc)))
        a = (cq.Workplane("YZ").circle(3.175).extrude(6.0).translate((ox1, y, zc))
             .union(cq.Workplane("YZ").polygon(6, 8.0 / 0.866).extrude(2.0).translate((ox1, y, zc))))
        if length > 0:   # straight (or tilt/swivel) rubber-duck antenna, pointing up
            a = a.union(cq.Workplane("YZ").circle(5.0).extrude(16.0).translate((ox1 + 6.0, y, zc)))
            a = a.union(cq.Workplane("YZ").circle(4.0).extrude(length).translate((ox1 + 22.0, y, zc)))
        else:            # cable plug of an external active GPS antenna
            a = a.union(cq.Workplane("YZ").circle(4.0).extrude(12.0).translate((ox1 + 6.0, y, zc)))
            a = a.union(cq.Workplane("XY").circle(1.5).extrude(-45.0).translate((ox1 + 14.0, y, zc)))
        ant_out.append(a)
    parts["antennas"] = union_all(ant_out)
    parts["sma_bulkheads"] = union_all(ant_in)
    sma_ys = [a[1] for a in p["antennas"]]
    top_slots = []
    for y in range(60, int(iy1) - 8, 4):
        if all(abs(y + 1 - s) > 7 for s in sma_ys):
            top_slots.append(box(ix1 - 1, y, z_back_in + 4, ox1 + 1, y + 2, z_front_in - 6))
    tub = tub.cut(union_all(top_slots))
    # plenum divider: keeps the fan pulling through the SoC column, the cell column breathes passively
    parts["plenum_divider"] = box(p["sbc_w"] + p["clear"], 55.5, z_back_in, ix1, 57.0, z_front_in - disp_t - 0.5)
    # --- bottom wall: intake slots for both columns
    bot = []
    for y in list(range(10, 52, 4)) + list(range(60, 136, 4)):
        bot.append(box(ox0 - 1, y, z_back_in + 3, ix0 + 1, y + 2, z_front_in - 6))
    tub = tub.cut(union_all(bot))
    # --- back: battery door opening + vent slots behind the SoC column
    tub = tub.cut(box(x0 + 2, p["cells_y0"] + 2, z_out_back - 1, x0 + p["cell_len"] - 2,
                      p["cells_y0"] + 4 * p["cell_pitch"] - 2, z_back_in + 1))
    tub = tub.cut(union_all([box(8 + i * 6, 6, z_out_back - 1, 11 + i * 6, 48, z_back_in + 1) for i in range(12)]))
    parts["enclosure_tub"] = tub
    parts["front_plate"] = front
    # air-flow arrows (visual only): up the SoC chimney into the fan, passive up the cell column
    arrows = []
    for (y, z, x_from, x_to) in ((20, 4, 2, 70), (45, 4, 2, 70), (30, 16, 2, 70),
                                 (90, -8, 2, 80), (120, 16, 2, 80)):
        shaft = cq.Workplane("YZ").circle(0.8).extrude(x_to - x_from - 6).translate((x_from, y, z))
        head = cq.Workplane("YZ").circle(2.5).workplane(offset=6).circle(0.1).loft().translate((x_to - 6, y, z))
        arrows.append(shaft.union(head))
    parts["airflow"] = union_all(arrows)
    geo = dict(ox0=ox0, ox1=ox1, oy0=oy0, oy1=oy1, zb=z_out_back, zf=z_out_front)
    dims = dict(outer=(round(ox1 - ox0, 1), round(oy1 - oy0, 1), round(z_out_front - z_out_back, 1)),
                display_fits=(p["disp_h"] <= ix1 - ix0 - 8.0, p["disp_w"] <= iy1 - iy0 - 8.0))
    return parts, dims, geo


def to_world(wp, p, geo):
    """Stand the box up: board +X -> world up, display (+Z) -> towards the viewer (-X), then tilt back."""
    w = wp.rotate((0, 0, 0), (0, 1, 0), -90)
    return w.rotate((0, 0, 0), (0, 1, 0), p["tilt"])


def build_stand(p, geo, world_parts):
    """Two cradles under the tilted box: keep a gap for the bottom intake slots and widen the footprint."""
    env = to_world(box(geo["ox0"], geo["oy0"], geo["zb"], geo["ox1"], geo["oy1"], geo["zf"]), p, geo)
    bb = env.val().BoundingBox()
    desk = bb.zmin - p["foot_gap"]
    cradles = []
    for y in p["cradle_y"]:
        blk = box(bb.xmin - 4, y, desk, bb.xmax + p["stand_depth"], y + p["cradle_w"], bb.zmin + 22)
        cradles.append(blk.cut(env).cut(env.translate((0, 0, 30))))
    stand = union_all(cradles)
    return stand, desk


COLORS = dict(bubblegum96=(0.18, 0.49, 0.20), soc_heatsink=(0.75, 0.75, 0.78), ls_connector=(0.13, 0.13, 0.13),
              main_board=(0.08, 0.40, 0.75), antennas=(0.15, 0.15, 0.15), sma_bulkheads=(0.83, 0.69, 0.22),
              usb_c=(0.62, 0.62, 0.62), power_button=(0.90, 0.22, 0.21), mesh_button=(0.12, 0.53, 0.90),
              gps_switch=(1.0, 0.76, 0.03), gps_led=(0.2, 1.0, 0.2), fan=(0.2, 0.2, 0.25),
              plenum_divider=(0.55, 0.6, 0.62), airflow=(0.1, 0.6, 1.0),
              mesh_gps_zone=(0.56, 0.14, 0.67), power_zone=(0.94, 0.42, 0.0), mmdvm_zone=(0.0, 0.54, 0.48),
              cells_1s4p=(0.78, 0.16, 0.16), display=(0.10, 0.10, 0.12),
              standoffs=(0.85, 0.75, 0.35), enclosure_tub=(0.69, 0.75, 0.77), front_plate=(0.81, 0.85, 0.86), stand=(0.45, 0.47, 0.50))
OPACITY = dict(enclosure_tub=0.22, front_plate=0.18)


def render(parts, path, cam_pos, focal, skip=(), size=(1200, 900), opaque=False, zoom=1.0, fit=None):
    """Off-screen VTK render of the (world-space) parts to a PNG."""
    import vtk
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for name, wp in parts.items():
        if name in skip:
            continue
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(wp.val().toVtkPolyData(0.2, 0.3))
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*COLORS.get(name, (0.5, 0.5, 0.5)))
        op = 1.0 if (opaque and name in ("enclosure_tub", "front_plate")) else OPACITY.get(name, 1.0)
        actor.GetProperty().SetOpacity(op)
        ren.AddActor(actor)
    ren.SetUseDepthPeeling(True)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetAlphaBitPlanes(1)
    win.SetMultiSamples(0)
    win.AddRenderer(ren)
    win.SetSize(*size)
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*cam_pos)
    cam.SetViewUp(0, 0, 1)
    if fit:
        b = fit.val().BoundingBox()
        ren.ResetCamera((b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))
    else:
        ren.ResetCamera()
    ren.ResetCameraClippingRange()
    cam.Zoom(zoom)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.Update()
    w = vtk.vtkPNGWriter()
    w.SetFileName(path)
    w.SetInputConnection(grab.GetOutputPort())
    w.Write()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    parts, dims, geo = build()
    world = {n: to_world(wp, P, geo) for n, wp in parts.items()}
    stand, desk = build_stand(P, geo, world)
    world["stand"] = stand
    asm = cq.Assembly()
    for n, wp in world.items():
        asm.add(wp, name=n)
    asm.save(os.path.join(out, "concept_assembly.step"))
    # print orientation: tub on its back, front plate flat, cradles as modelled
    cq.exporters.export(parts["enclosure_tub"], os.path.join(out, "enclosure_tub.stl"))
    cq.exporters.export(parts["front_plate"], os.path.join(out, "front_plate.stl"))
    cq.exporters.export(stand, os.path.join(out, "stand_cradle.stl"))
    shell = world["enclosure_tub"]
    b = shell.val().BoundingBox()
    focal = ((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, (b.zmin + b.zmax) / 2 + 20)
    render(world, os.path.join(out, "preview_desk_front.png"), (-420, -260, 230), focal, opaque=True,
           skip=("airflow",), zoom=1.0)
    render(world, os.path.join(out, "preview_desk_back.png"), (420, 300, 200), focal, opaque=True,
           skip=("airflow",), zoom=1.0)
    render(world, os.path.join(out, "preview_airflow.png"), (-300, -360, 120), focal,
           skip=("front_plate", "display", "antennas", "stand"), fit=shell, zoom=1.05)
    render(world, os.path.join(out, "preview_inside.png"), (-330, -200, 160), focal,
           skip=("front_plate", "display", "antennas", "airflow", "stand"), fit=shell, zoom=1.05)
    tilt_h = round(max(w.val().BoundingBox().zmax for w in world.values()) - desk, 1)
    print("outer (W x D x H, board frame) mm:", dims["outer"], "| standing height incl. antennas:", tilt_h,
          "| display clears corner posts:", dims["display_fits"])
