#!/usr/bin/env python3
"""
workboy_case_b123d.py — build123d port of the WorkBoy case.

Same parametric two-piece clamshell as workboy_case.scad, but in Python/build123d
so it can import the KiCad board STEP for fit/alignment and export STL + STEP.

Run: python workboy_case_b123d.py
  -> case/workboy_top.stl, case/workboy_bottom.stl, case/workboy_case_assembly.step
If kicad/workboy_board.step exists it is imported and placed on the standoffs
(generate a placeholder with: python kicad/make_board_step.py).
"""
import os, sys
from build123d import (BuildPart, BuildSketch, Plane, Locations,
                       RectangleRounded, Rectangle, Circle, Box,
                       extrude, Mode, Compound, Location,
                       export_stl, export_step, import_step)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "layout"))
from keymap import centers, LAYOUT_COLS, LAYOUT_ROWS

# ---- parameters (mm) — key layout comes from layout/keymap.py ----
PITCH = 12                       # must match layout/gen_layout.py
KEY_GAP = 2.0                    # cap clearance: cutout = key cell minus this
MARGIN, PLATE_TH, WALL, FLOOR_TH = 8, 2.0, 2.4, 2.0
CASE_H, STANDOFF_H = 20, 6.0
SCREW_D, BOSS_OD, INSERT_D, PCB_INSET = 2.9, 7, 3.4, 7

field_w, field_h = LAYOUT_COLS * PITCH, LAYOUT_ROWS * PITCH
CASE_W, CASE_D = field_w + 2 * MARGIN, field_h + 2 * MARGIN
cox = CASE_W / 2 - BOSS_OD / 2 - WALL * 0.5
coy = CASE_D / 2 - BOSS_OD / 2 - WALL * 0.5
sx, sy = CASE_W / 2 - (BOSS_OD + PCB_INSET), CASE_D / 2 - (BOSS_OD + PCB_INSET)
bosses = [(cox, coy), (-cox, coy), (cox, -coy), (-cox, -coy)]
stands = [(sx, sy), (-sx, sy), (sx, -sy), (-sx, -sy)]

# ---- bottom tray ----
with BuildPart() as bottom:
    with BuildSketch():
        RectangleRounded(CASE_W, CASE_D, 2)
    extrude(amount=CASE_H)
    with BuildSketch(Plane.XY.offset(FLOOR_TH)):                  # hollow
        RectangleRounded(CASE_W - 2 * WALL, CASE_D - 2 * WALL, 2)
    extrude(amount=CASE_H - FLOOR_TH + 0.1, mode=Mode.SUBTRACT)
    with BuildSketch():                                           # screw bosses
        with Locations(*bosses):
            Circle(BOSS_OD / 2)
    extrude(amount=CASE_H)
    with BuildSketch(Plane.XY.offset(CASE_H - 8)):                # insert pockets
        with Locations(*bosses):
            Circle(INSERT_D / 2)
    extrude(amount=8.1, mode=Mode.SUBTRACT)
    with BuildSketch():                                           # PCB standoffs
        with Locations(*stands):
            Circle(2.5)
    extrude(amount=FLOOR_TH + STANDOFF_H)
    with Locations((0, CASE_D / 2 - WALL, CASE_H - 6)):           # cable slot
        Box(12, WALL * 3, 8, mode=Mode.SUBTRACT)

# ---- top plate (key cutouts at the real layout positions) ----
keycells = centers(PITCH)        # (cx, cy, width_units) per key, origin-centred
with BuildPart() as top:
    with BuildSketch(Plane.XY.offset(CASE_H)):
        RectangleRounded(CASE_W, CASE_D, 2)
        for cx, cy, w in keycells:
            with Locations((cx, cy)):
                Rectangle(w * PITCH - KEY_GAP, PITCH - KEY_GAP, mode=Mode.SUBTRACT)
        with Locations(*bosses):
            Circle(SCREW_D / 2, mode=Mode.SUBTRACT)
    extrude(amount=PLATE_TH)

# ---- export ----
export_stl(bottom.part, os.path.join(HERE, "workboy_bottom.stl"))
export_stl(top.part,    os.path.join(HERE, "workboy_top.stl"))

parts = [bottom.part, top.part]
board_step = os.path.join(HERE, "..", "kicad", "workboy_board.step")
if os.path.exists(board_step):
    board = import_step(board_step).move(Location((0, 0, FLOOR_TH + STANDOFF_H)))
    board.label = "PCB"
    parts.append(board)
    print("imported board STEP -> placed on standoffs")
else:
    print("no board STEP found (run kicad/make_board_step.py first); case only")

export_step(Compound(children=parts), os.path.join(HERE, "workboy_case_assembly.step"))
print(f"case = {CASE_W:.0f} x {CASE_D:.0f} x {CASE_H + PLATE_TH:.0f} mm")
print("exported: workboy_top.stl, workboy_bottom.stl, workboy_case_assembly.step")
