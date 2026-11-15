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
    pcb_t=1.6, pcb_y1=-1.0, pcb_y2=166.0,
    disp_ref_y2=153.0,          # the display keeps its place: the 13 mm added for the RJ45 lie beyond its +Y end
    edge_gap=2.4,               # +Y board edge to the inner wall: the switch levers (1.25 / 1.9) and console pins (1.6)
                                # stay inside it, so the board stack drops straight in from the front
    pcb_wide=(-2.0, 88.5, 54.0),               # L-shaped main board: x -2 .. 88.5 from y = 54 (cell holders)
    mb_holes_ext=[(4.0, 150.0), (84.0, 162.0)],   # main-board holes beyond the last cell holder
    # 4x Keystone 1042P, mounted on the main-board underside, cells along X (vertical when standing)
    cell_len=77.1, cell_pitch=21.8, cell_h=20.5, cells_y0=55.0, cell_cx=43.25,   # Keystone 1042 courtyard 88 x 21.75
    # display: TJC8048X550_011R (resistive: 4-pin touch tail HST050008), TJC X5 datasheet p.7; long side along Y
    disp_w=136.9, disp_h=84.0, disp_pcb=1.6, disp_holes=(130.5, 77.6),
    lcd_w=120.7, lcd_h=75.8, lcd_t=4.5,         # front stack: 4.5 (R, this unit); 3.3 (N) / 5.08 (C)
    disp_back=6.0,                              # tallest part behind the PCB (XH connector)
    touch_gap=0.5,                              # keep the bezel off the touch film
    va_w=108.0, va_h=64.8, va_off=1.94,         # active area, offset away from the FPC edge
    # enclosure
    wall=2.5, back=2.5, front=2.5, clear=1.0,
    bottom_wall=7.0,            # thick bottom rail: carries two front-plate screw bosses outside the board stack
    # front "chin" under the 5" display: Meshtastic OLED + MESH button on a small front-panel board
    chin=26.0,
    # Heltec 1.3" SH1106 I2C module (HTDS-WI13/BI13): PCB, M2 hole spacing, glass, active area (y, x)
    oled_module=(35.5, 32.0, 1.6), oled_holes=(25.4, 27.7), oled_glass=(34.5, 23.0, 1.8),
    oled_va=(29.42, 14.7), oled_va_dx=0.0,      # active-area offset on the module: MEASURE the real part
    # front-panel board (hardware/r3.0-study/front_panel): 26 x 20 mm, F side 5 mm behind the front plate
    fp_pcb=(26.0, 20.0), fp_gap=5.0, fp_dy=3.0,  # fp_dy: gap to the OLED module (viewer's right is -Y)
    top_parts=9.0,              # tallest part on the main-board top
    plenum=13.0,                # top air plenum (fan, SMA bodies, pigtails) beyond X = 85
    # fan: 30x30x10 mm 5 V, axis along X, exhausting up through the top wall
    fan=30.0, fan_t=10.0, fan_y=38.0, fan_holes=24.0,
    # antennas on the top wall: bulkhead SMA-female + IPEX pigtail (label, y, whip length; 0 = cable)
    # 433 TX and 433 RX at the two ends for the best duplex isolation.
    antennas=[("433 TX", 12.0, 195.0), ("GPS", 70.0, 0.0), ("LoRa 920", 100.0, 110.0), ("433 RX", 128.0, 195.0)],
    sma_hole=6.5, sma_flat=5.9,  # D-hole for 1/4"-36 bulkhead SMA (check the actual part)
    # print / assembly details
    tol=0.25,                   # general clearance between printed parts
    corner_r=3.0,               # outer vertical corner radius
    lip_t=1.2, lip_h=2.0,       # locating rim on the front plate, fits inside the tub walls
    ins_m3=4.0, ins_m25=3.6,    # pilot holes for M3 / M2.5 heat-set inserts (check your inserts)
    door_t=1.5, door_margin=2.5,  # battery door plate thickness and overlap around the opening
    label_depth=0.4,
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
    wx0, wx1, wy = p["pcb_wide"]
    mb = box(0, p["pcb_y1"], z_mb, p["sbc_w"], wy, z_mt).union(box(wx0, wy, z_mb, wx1, p["pcb_y2"], z_mt))
    for (hx, hy) in p["sbc_holes"] + p["mb_holes_ext"]:
        mb = mb.cut(cq.Workplane("XY").circle(1.35).extrude(5).translate((hx, hy, z_mb - 1)))
    parts["main_board"] = mb
    # side-panel controls on the +Y edge: USB-C, MESH button, power button, GPS switch, GPS LED
    y2 = p["pcb_y2"]
    # +Y edge parts as placed by hardware/r3.0-study/gen/main_pcb.py (x centres 9 / 23.7 / 33.7 / 42.1 / 53 / 60.8 / 71.3)
    parts["usb_c"] = box(19.2, y2 - 7.3, z_mt, 28.2, y2 + 0.6, z_mt + 3.3)
    # RJ45 with magnetics (HanRun HR911105A): 16 x 21.3 x 13.4 mm, front 1 mm beyond the board edge
    parts["rj45"] = box(71.3 - 8.0, y2 + 1.0 - 21.3, z_mt, 71.3 + 8.0, y2 + 1.0, z_mt + 13.4)
    # Alps SKRTLAE010 (manufacturer STEP): body 4.5 x 2.96 x 3.3 mm, round 2 mm stem at mid height,
    # guide bosses 1.85 mm inside the board edge, stem tip 0.2 mm beyond the edge
    parts["power_button"] = (box(31.45, y2 - 3.35, z_mt, 35.95, y2 - 0.39, z_mt + 3.3)
                             .union(cq.Workplane("XZ").center(33.7, z_mt + 1.65).circle(1.0).extrude(-0.59)
                                    .translate((0, y2 - 0.39, 0))))
    parts["gps_switch"] = (box(38.75, y2 - 2.9, z_mt, 45.45, y2 - 0.2, z_mt + 1.4)             # C&K PCM12
                           .union(box(41.45, y2 - 0.2, z_mt + 0.2, 42.75, y2 + 1.25, z_mt + 1.2)))  # lever (centre)
    # battery master switch, C&K JS202011AQN (DPDT, right angle): body 9.1 x 6.1 x 3.5 mm ending 0.12 mm inside
    # the edge; lever 2 x 2 mm, 2 mm long, 2 mm travel -- lever dimensions assumed, CHECK against the part
    parts["battery_switch"] = (box(48.45, y2 - 6.22, z_mt, 57.55, y2 - 0.12, z_mt + 3.5)
                               .union(box(52.0, y2 - 0.12, z_mt + 0.75, 54.0, y2 + 1.9, z_mt + 2.75)))
    parts["gps_led"] = box(59.8, y2 - 3.0, z_mt, 61.8, y2 - 1.0, z_mt + 1)
    # Bubblegum-96 console: 6-pin 2.54 mm right-angle header, FTDI order, pin tips 1.6 mm beyond the edge
    parts["console_header"] = (box(1.1, y2 - 7.0, z_mt, 16.9, y2 - 4.4, z_mt + 2.54)
                               .union(box(2.0, y2 - 4.4, z_mt + 0.95, 16.0, y2 + 1.6, z_mt + 1.6)))
    # layout zones on the main-board top (standing: X is height)
    parts["mmdvm_zone"] = box(5, 2, z_mt, 80, 52, z_mt + 3)          # over the Bubblegum (SoC column)
    parts["mesh_gps_zone"] = box(5, 60, z_mt, 42, 136, z_mt + 3)     # low in the cell column
    parts["power_zone"] = box(46, 60, z_mt, 82, 136, z_mt + 5)       # top of the cell column: heat rises away
    # --- cells under the extension (vertical when standing)
    cells = []
    x0 = p["cell_cx"] - p["cell_len"] / 2
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
    ix0 = -p["clear"] - p["chin"]
    ix1 = p["sbc_w"] + p["clear"] + p["plenum"]
    iy0 = -2.0 - p["clear"]
    iy1 = p["pcb_y2"] + p["edge_gap"]
    ox0, ox1, oy0, oy1 = ix0 - p["bottom_wall"], ix1 + p["wall"], iy0 - p["wall"], iy1 + p["wall"]
    z_out_back = z_back_in - p["back"]
    z_out_front = z_front_in + p["front"]
    cx, cy = (-p["clear"] + ix1) / 2, (iy0 + p["disp_ref_y2"] + p["edge_gap"]) / 2   # 5" display above the chin,
    # centred on the board without the RJ45 strip so the 13.5 mm tall jack stays clear of its back
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
    tub = (box(ox0, oy0, z_out_back, ox1, oy1, z_front_in).edges("|Z").fillet(p["corner_r"])
           .cut(box(ix0, iy0, z_back_in, ix1, iy1, z_front_in + 1)))
    # corner posts for M3 heat-set inserts (front plate screws)
    posts, post_holes = [], []
    screw_pts = ((ix0 - p["bottom_wall"] / 2, iy0 + 6), (ix0 - p["bottom_wall"] / 2, iy1 - 6),
                 (ix1 - 4, iy0 + 4), (ix1 - 4, iy1 - 4))
    for (px, py) in screw_pts[2:]:
        posts.append(cq.Workplane("XY").circle(4.0).extrude(z_front_in - z_back_in).translate((px, py, z_back_in)))
    for (px, py) in screw_pts:
        post_holes.append(cq.Workplane("XY").circle(p["ins_m3"] / 2).extrude(10).translate((px, py, z_front_in - 8.0)))
    tub = tub.union(union_all(posts)).cut(union_all(post_holes))
    # stand-offs from the back: Bubblegum-96 holes (to its underside) and main-board extension holes
    ri = p["ins_m25"] / 2
    so = [cq.Workplane("XY").circle(3.5).extrude(-p["sbc_t"] - z_back_in).translate((hx, hy, z_back_in))
          .cut(cq.Workplane("XY").circle(ri).extrude(6.0).translate((hx, hy, -p["sbc_t"] - 6.0)))
          for (hx, hy) in p["sbc_holes"]]
    so += [cq.Workplane("XY").circle(3.5).extrude(z_mb - z_back_in).translate((hx, hy, z_back_in))
           .cut(cq.Workplane("XY").circle(ri).extrude(6.0).translate((hx, hy, z_mb - 6.0)))
           for (hx, hy) in p["mb_holes_ext"]]
    tub = tub.union(union_all(so))                 # printed bosses, M2.5 heat-set inserts
    parts["spacers_m25x8"] = union_all([cq.Workplane("XY").polygon(6, 5.0 / 0.866).circle(1.25).extrude(p["mezz_gap"])
                                        .translate((hx, hy, 0.0)) for (hx, hy) in p["sbc_holes"]])
    front = box(ox0, oy0, z_front_in, ox1, oy1, z_out_front).edges("|Z").fillet(p["corner_r"])
    front = front.faces(">Z").edges().chamfer(0.6)
    t_ = p["tol"]
    rim = (box(ix0 + t_, iy0 + t_, z_front_in - p["lip_h"], ix1 - t_, iy1 - t_, z_front_in)
           .cut(box(ix0 + t_ + p["lip_t"], iy0 + t_ + p["lip_t"], z_front_in - p["lip_h"] - 1,
                    ix1 - t_ - p["lip_t"], iy1 - t_ - p["lip_t"], z_front_in + 1)))
    for (px, py) in screw_pts[2:]:                  # clear the two plenum posts
        rim = rim.cut(cq.Workplane("XY").circle(4.0 + t_).extrude(p["lip_h"] + 2).translate((px, py, z_front_in - p["lip_h"] - 1)))
    front = front.union(rim)
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
    # chin: Heltec OLED module screwed to the front plate (glass against the plate) and the front-panel
    # board (MESH button + LED) to its right, both under the 5" display
    mw, mh, mt = p["oled_module"]
    gw, gh, gt = p["oled_glass"]
    xm = (cx - p["disp_h"] / 2) - 1.0 - mh / 2          # module top 1 mm below the 5" display PCB
    z_glass = z_front_in - gt
    parts["oled"] = (box(xm - mh / 2, cy - mw / 2, z_glass - mt, xm + mh / 2, cy + mw / 2, z_glass)
                     .union(box(xm - gh / 2, cy - gw / 2, z_glass, xm + gh / 2, cy + gw / 2, z_front_in)))
    hy, hx = p["oled_holes"][0] / 2, p["oled_holes"][1] / 2
    ob = [cq.Workplane("XY").circle(2.0).circle(0.8).extrude(gt).translate((xm + sx * hx, cy + sy * hy, z_glass))
          for sx in (-1, 1) for sy in (-1, 1)]
    front = front.union(union_all(ob))                    # M2 self-tapping bosses
    vw, vh = p["oled_va"]
    xv = xm + p["oled_va_dx"]
    front = front.cut(box(xv - vh / 2 - 0.5, cy - vw / 2 - 0.5, z_front_in - 1, xv + vh / 2 + 0.5, cy + vw / 2 + 0.5,
                          z_out_front + 1))
    # front-panel board: local (u, v) = (viewer's right, down) -> model (Y = y_left - u, X = x_top - v)
    pw_, ph_ = p["fp_pcb"]
    y_left = cy - mw / 2 - p["fp_dy"]
    x_top = xm + ph_ / 2
    z_fpf = z_front_in - p["fp_gap"]
    def fpl(u, v):
        return x_top - v, y_left - u
    parts["chin_board"] = box(x_top - ph_, y_left - pw_, z_fpf - 1.6, x_top, y_left, z_fpf)
    bx, by = fpl(8.25, 12.0)
    parts["mesh_button"] = (box(bx - 3, by - 3, z_fpf, bx + 3, by + 3, z_fpf + 3.5)
                            .union(cq.Workplane("XY").circle(1.75).extrude(8.0 - 3.5).translate((bx, by, z_fpf + 3.5))))
    lx, ly = fpl(20.0, 9.0)
    parts["fp_led"] = box(lx - 0.65, ly - 1.0, z_fpf, lx + 0.65, ly + 1.0, z_fpf + 0.8)
    fb = []
    for (u, v) in ((3.0, 3.0), (23.0, 3.0)):
        hx_, hy_ = fpl(u, v)
        fb.append(cq.Workplane("XY").circle(2.5).circle(1.1).extrude(p["fp_gap"]).translate((hx_, hy_, z_fpf)))
    front = front.union(union_all(fb))                    # M2.5 self-tapping bosses
    front = front.cut(cq.Workplane("XY").circle(2.1).extrude(10).translate((bx, by, z_front_in - 2)))   # button
    front = front.cut(cq.Workplane("XY").circle(1.5).extrude(10).translate((lx, ly, z_front_in - 2)))   # LED
    for (px, py) in screw_pts:
        front = front.cut(cq.Workplane("XY").circle(1.7).extrude(10).translate((px, py, z_front_in - 3)))
        front = front.cut(cq.Workplane("XY").circle(3.1).extrude(2).translate((px, py, z_out_front - 1.3)))   # head
    # side face (Y = 0): Bubblegum ports
    for (a, b, zt) in ((2, 14, 2.6), (17.5, 32.5, 7.0), (38, 45, 4.0), (49.5, 63.7, 8.0), (69, 83, 8.0)):
        tub = tub.cut(box(a - 0.5, oy0 - 1, -p["sbc_t"] - 0.5, b + 0.5, iy0 + 1, zt))
    # side face (+Y): console, USB-C (opening passes the plug overmold), power-button cap, GPS slider, LED
    tub = tub.cut(box(1.0, iy1 - 1, z_mt - 0.4, 17.0, oy1 + 1, z_mt + 3.2))          # 6-pin Dupont / FTDI housing
    tub = tub.cut(box(17.5, iy1 - 1, z_mt - 2.0, 29.9, oy1 + 1, z_mt + 5.3))         # 12.4 x 7.3 mm for the USB-C plug
    tub = tub.cut(box(71.3 - 8.5, iy1 - 1, z_mt - 0.3, 71.3 + 8.5, oy1 + 1, z_mt + 14.0))   # RJ45 mouth
    tub = tub.cut(cq.Workplane("XZ").center(60.8, z_mt + 2.2).circle(1.6).extrude(-10).translate((0, iy1 - 2, 0)))
    t2 = p["tol"]
    # power button cap: nub on the plunger, flange in a pocket of the inner wall face, stem through the wall
    bz = z_mt + 1.65                      # stem axis of the SKRTLAE010
    tub = tub.cut(cq.Workplane("XZ").center(33.7, bz).circle(1.8 + t2).extrude(-10).translate((0, iy1 - 1, 0)))
    tub = tub.cut(box(33.7 - 3.3, iy1 - 0.1, bz - 2.5, 33.7 + 3.3, iy1 + 1.0, bz + 2.5))
    parts["button_cap"] = (cq.Workplane("XZ").center(33.7, bz).circle(1.0).extrude(-(iy1 - y2 - 0.3)).translate((0, y2 + 0.3, 0))
                           .union(box(33.7 - 3.0, iy1, bz - 2.2, 33.7 + 3.0, iy1 + 0.8, bz + 2.2))
                           .union(cq.Workplane("XZ").center(33.7, bz).circle(1.8).extrude(-(oy1 + 0.8 - iy1 - 0.8))
                                  .translate((0, iy1 + 0.8, 0))))
    # GPS slider cap: grips the PCM12 lever (pocket open towards the front so the board drops in), 2 mm travel
    sx = 42.1
    tub = tub.cut(box(sx - 3.0, iy1 - 1, z_mt - 0.4, sx + 3.0, oy1 + 1, z_mt + 2.6))
    tub = tub.cut(box(sx - 4.6, iy1 - 0.1, z_mt - 1.6, sx + 4.6, iy1 + 1.0, z_mt + 3.8))
    parts["slider_cap"] = (box(sx - 1.8, y2 + 0.3, z_mt - 0.2, sx + 1.8, iy1, z_mt + 2.2)
                           .cut(box(sx - 0.8, y2 + 0.2, z_mt + 0.1, sx + 0.8, y2 + 1.45, z_mt + 2.3))
                           .union(box(sx - 3.6, iy1, z_mt - 1.4, sx + 3.6, iy1 + 0.8, z_mt + 3.6))
                           .union(box(sx - 1.8, iy1 + 0.8, z_mt - 0.2, sx + 1.8, oy1 + 0.8, z_mt + 2.4)))
    # battery switch cap: same idea for the JS202011 lever (2 x 2 mm, 2 mm travel)
    bx = 53.0
    tub = tub.cut(box(bx - 3.3, iy1 - 1, z_mt - 0.1, bx + 3.3, oy1 + 1, z_mt + 3.7))
    tub = tub.cut(box(bx - 5.2, iy1 - 0.1, z_mt - 1.3, bx + 5.2, iy1 + 1.0, z_mt + 4.9))
    parts["battery_cap"] = (box(bx - 2.1, y2 + 0.3, z_mt + 0.1, bx + 2.1, iy1, z_mt + 3.5)
                            .cut(box(bx - 1.1, y2 + 0.2, z_mt + 0.6, bx + 1.1, y2 + 2.1, z_mt + 3.6))
                            .union(box(bx - 4.2, iy1, z_mt - 1.1, bx + 4.2, iy1 + 0.8, z_mt + 4.7))
                            .union(box(bx - 2.1, iy1 + 0.8, z_mt + 0.1, bx + 2.1, oy1 + 0.8, z_mt + 3.5)))
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
    tub = tub.union(box(p["pcb_wide"][1] + 0.5, 53.5, z_back_in, ix1, 54.5, z_front_in - disp_t - 0.5))
    # --- bottom wall: intake slots for both columns
    bot = []
    for y in list(range(10, 52, 4)) + list(range(60, 136, 4)):
        bot.append(box(ox0 - 1, y, z_back_in + 3, ix0 + 1, y + 2, z_front_in - 6))
    tub = tub.cut(union_all(bot))
    # --- back: battery door opening + vent slots behind the SoC column
    dx0, dx1 = x0 + 2, x0 + p["cell_len"] - 2
    dy0, dy1 = p["cells_y0"] + 2, p["cells_y0"] + 4 * p["cell_pitch"] - 2
    tub = tub.cut(box(dx0, dy0, z_out_back - 1, dx1, dy1, z_back_in + 1))
    m_, dt = p["door_margin"], p["door_t"]
    ear_x = dx1 + 7.0                                # screw ears beyond the cell holders (x ~ 86.8)
    ear_ys = (dy0 + 14.0, dy1 - 14.0)
    recess = box(dx0 - m_, dy0 - m_, z_out_back - 1, dx1 + m_, dy1 + m_, z_out_back + dt)
    door = box(dx0 - m_ + t_, dy0 - m_ + t_, z_out_back, dx1 + m_ - t_, dy1 + m_ - t_, z_out_back + dt)
    for ey in ear_ys:
        recess = recess.union(box(dx1, ey - 5.0, z_out_back - 1, ear_x + 4.5, ey + 5.0, z_out_back + dt))
        door = door.union(box(dx1, ey - 5.0 + t_, z_out_back, ear_x + 4.5 - t_, ey + 5.0 - t_, z_out_back + dt))
        tub = tub.union(cq.Workplane("XY").circle(3.8).extrude(7.0).translate((ear_x, ey, z_back_in)))
    tub = tub.cut(recess)
    for ey in ear_ys:
        tub = tub.cut(cq.Workplane("XY").circle(p["ins_m3"] / 2).extrude(12).translate((ear_x, ey, z_out_back)))
        door = door.cut(cq.Workplane("XY").circle(1.7).extrude(5).translate((ear_x, ey, z_out_back - 1)))
        door = door.cut(cq.Workplane("XY").circle(3.1).extrude(1.0).translate((ear_x, ey, z_out_back - 0.2)))
    for ty in (dy0 + 12.0, (dy0 + dy1) / 2 - 5.0, dy1 - 22.0):   # tongues hook under the back wall at the -X edge
        door = door.union(box(dx0 + t_, ty, z_out_back + dt, dx0 + t_ + 1.6, ty + 10.0, z_back_in + 1.4))
        door = door.union(box(dx0 - 3.0, ty, z_back_in + t_, dx0 + t_ + 1.6, ty + 10.0, z_back_in + 1.4))
    for i in range(4):                              # vent slots along each cell
        yc = p["cells_y0"] + i * p["cell_pitch"] + 10.35
        door = door.cut(box(dx0 + 10, yc - 1.0, z_out_back - 1, dx1 - 10, yc + 1.0, z_out_back + dt + 1))
    parts["battery_door"] = door
    tub = tub.cut(union_all([box(8 + i * 6, 6, z_out_back - 1, 11 + i * 6, 48, z_back_in + 1) for i in range(12)]))
    ld = p["label_depth"]

    def label(txt, size, pos, rot, depth_dir):
        """Text solid, ld deep, lying in the XY plane then rotated/translated into place."""
        t = cq.Workplane("XY").text(txt, size, ld + 0.2, halign="center", valign="center")
        for (axis, ang) in rot:
            t = t.rotate((0, 0, 0), axis, ang)
        return t.translate(pos)
    try:
        # +Y side face (left side when standing): reads along +Z with +X up, beside each opening
        side = [("UART", 9.0), ("USB-C", 23.7), ("PWR", 33.7), ("GPS", 42.1), ("BAT", 53.0), ("LAN", 71.3)]
        for (txt, x) in side:
            tub = tub.cut(label(txt, 2.6, (x, oy1 - ld, z_mt + (18.5 if txt == "LAN" else 13.5)), [((1, 1, 1), -120)], None))
        # top wall: antenna names in front of the SMA holes, read from the front (along -Y)
        for (name, y, _l) in p["antennas"]:
            tub = tub.cut(label(name, 2.6, (ox1 - ld, y, zc + 8.5), [((0, 1, 0), 90), ((1, 0, 0), -90)], None))
        # front plate: reads along -Y with +X up
        front = front.cut(label("MESH", 3.0, (bx - 6.5, by, z_out_front - ld), [((0, 0, 1), -90)], None))
        parts["_labels_ok"] = None
    except Exception as e:  # noqa: BLE001  (no font available: skip the labels)
        print("labels skipped:", e)
    parts.pop("_labels_ok", None)
    parts["enclosure_tub"] = tub
    parts["front_plate"] = front
    # air-flow arrows (visual only): up the SoC chimney into the fan, passive up the cell column
    arrows = []
    xa = ix0 + 4
    for (y, z, x_from, x_to) in ((20, 4, xa, 70), (45, 4, xa, 70), (30, 16, xa, 70),
                                 (90, -8, xa, 80), (120, 16, xa, 80)):
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
    y0_, y1_ = min(p["cradle_y"]), max(p["cradle_y"]) + p["cradle_w"]
    tie = box(bb.xmax + p["stand_depth"] - 10.0, y0_, desk, bb.xmax + p["stand_depth"], y1_, desk + 6.0)
    tie2 = box(bb.xmin - 4, y0_, desk, bb.xmin + 4, y1_, desk + 4.0)
    stand = union_all(cradles + [tie, tie2])
    return stand, desk


COLORS = dict(bubblegum96=(0.18, 0.49, 0.20), soc_heatsink=(0.75, 0.75, 0.78), ls_connector=(0.13, 0.13, 0.13),
              main_board=(0.08, 0.40, 0.75), antennas=(0.15, 0.15, 0.15), sma_bulkheads=(0.83, 0.69, 0.22),
              usb_c=(0.62, 0.62, 0.62), power_button=(0.90, 0.22, 0.21), mesh_button=(0.12, 0.53, 0.90),
              gps_switch=(1.0, 0.76, 0.03), gps_led=(0.2, 1.0, 0.2), fan=(0.2, 0.2, 0.25),
              console_header=(0.1, 0.1, 0.1), chin_board=(0.1, 0.45, 0.2), oled=(0.02, 0.02, 0.05),
              fp_led=(0.2, 0.4, 1.0), button_cap=(0.9, 0.3, 0.25), slider_cap=(1.0, 0.76, 0.03), battery_cap=(0.2, 0.7, 0.3), battery_switch=(0.3, 0.3, 0.3), rj45=(0.7, 0.7, 0.7), battery_door=(0.55, 0.62, 0.66), spacers_m25x8=(0.85, 0.75, 0.35),
              airflow=(0.1, 0.6, 1.0),
              mesh_gps_zone=(0.56, 0.14, 0.67), power_zone=(0.94, 0.42, 0.0), mmdvm_zone=(0.0, 0.54, 0.48),
              cells_1s4p=(0.78, 0.16, 0.16), display=(0.10, 0.10, 0.12),
              enclosure_tub=(0.69, 0.75, 0.77), front_plate=(0.81, 0.85, 0.86), stand=(0.45, 0.47, 0.50))
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
    # print orientation: tub on its back, front plate face down, door outside face down, stand as modelled
    prints = {"enclosure_tub": parts["enclosure_tub"],
              "front_plate": parts["front_plate"].rotate((0, 0, 0), (0, 1, 0), 180),
              "battery_door": parts["battery_door"],
              "button_cap": parts["button_cap"].rotate((0, 0, 0), (1, 0, 0), -90),
              "slider_cap": parts["slider_cap"].rotate((0, 0, 0), (1, 0, 0), -90),
              "battery_cap": parts["battery_cap"].rotate((0, 0, 0), (1, 0, 0), -90),
              "stand": stand}
    for n, wp in prints.items():
        cq.exporters.export(wp, os.path.join(out, n + ".stl"), tolerance=0.05, angularTolerance=0.2)
        cq.exporters.export(wp, os.path.join(out, n + ".step"))
        b_ = wp.val().BoundingBox()
        print("  %-14s %6.1f x %6.1f x %5.1f mm  %6.1f cm3" % (n, b_.xlen, b_.ylen, b_.zlen, wp.val().Volume() / 1000))
    shell = world["enclosure_tub"]
    b = shell.val().BoundingBox()
    focal = ((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, (b.zmin + b.zmax) / 2 + 20)
    render(world, os.path.join(out, "preview_desk_front.png"), (-420, -260, 230), focal, opaque=True,
           skip=("airflow",), zoom=1.0)
    render(world, os.path.join(out, "preview_desk_back.png"), (420, 300, 200), focal, opaque=True,
           skip=("airflow",), zoom=1.0)
    render(world, os.path.join(out, "preview_airflow.png"), (-300, -360, 120), focal,
           skip=("front_plate", "display", "antennas", "stand"), fit=shell, zoom=1.05)
    render(world, os.path.join(out, "preview_side_ports.png"), (60, 420, 60), focal, opaque=True,
           skip=("airflow", "antennas"), zoom=1.3)
    render(world, os.path.join(out, "preview_top_labels.png"), (-260, 60, 420), focal, opaque=True,
           skip=("airflow", "antennas"), zoom=1.3)
    render(world, os.path.join(out, "preview_inside.png"), (-330, -200, 160), focal,
           skip=("front_plate", "display", "antennas", "airflow", "stand"), fit=shell, zoom=1.05)
    tilt_h = round(max(w.val().BoundingBox().zmax for w in world.values()) - desk, 1)
    print("outer (W x D x H, board frame) mm:", dims["outer"], "| standing height incl. antennas:", tilt_h,
          "| display clears corner posts:", dims["display_fits"])
