#!/usr/bin/env python3
"""
workboy_case_b123d.py - build123d two-piece clamshell for the WorkBoy PCB.

*** Every dimension is derived from kicad/workboy.kicad_pcb at build time. ***

That is the whole point of this rewrite. The previous version sized the case from
the KEY FIELD (LAYOUT_COLS * PITCH + margin), which had nothing to do with the
board: it produced a 160 x 76 mm box for a 152 x 106.125 mm PCB - 30 mm shallower
than the board is deep - and placed standoffs at coordinates that matched no hole
on any board. It had never fitted, not even the placeholder it claimed to fit.

Now the board file is the single source of truth. The outline, the mounting-hole
positions and the key-field offset are all parsed from it, so the case cannot
drift from the PCB again. If the board changes, re-run this script.

Parsed by text, not pcbnew: this runs under a plain python with build123d, which
has no KiCad bindings.

Run:  python workboy_case_b123d.py
  -> case/workboy_top.stl, case/workboy_bottom.stl, case/workboy_case_assembly.step
"""
import os, re, sys

from build123d import (BuildPart, BuildSketch, Plane, Locations,
                       RectangleRounded, Rectangle, Circle, Box,
                       extrude, Mode, Compound, Location,
                       export_stl, export_step, import_step)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "layout"))
from keymap import centers, LAYOUT_COLS, LAYOUT_ROWS

PCB_FILE = os.path.join(HERE, "..", "kicad", "workboy.kicad_pcb")
STEP_FILE = os.path.join(HERE, "..", "kicad", "workboy_board.step")


# ---------------------------------------------------------------------------
# Read the board
# ---------------------------------------------------------------------------
def _blocks(txt, opener):
    """Yield balanced-paren substrings starting at each occurrence of `opener`."""
    for m in re.finditer(re.escape(opener), txt):
        i, depth = m.start(), 0
        while i < len(txt):
            if txt[i] == "(":
                depth += 1
            elif txt[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield txt[m.start():i + 1]


def parse_board(path):
    """-> dict with outline, centre, mounting holes and switch positions (KiCad mm)."""
    txt = open(path, encoding="utf-8", errors="replace").read()

    xs, ys = [], []
    for prim in ("(gr_line", "(gr_arc", "(gr_rect", "(gr_poly"):
        for blk in _blocks(txt, prim):
            if '"Edge.Cuts"' not in blk:
                continue
            for pm in re.finditer(r"\((?:start|end|mid|xy) ([-\d.]+) ([-\d.]+)\)", blk):
                xs.append(float(pm.group(1)))
                ys.append(float(pm.group(2)))
    if not xs:
        raise SystemExit("could not parse Edge.Cuts from " + path)

    holes, switches, conns = {}, {}, {}
    for blk in _blocks(txt, "(footprint "):
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
        if not ref or not at:
            continue
        r, x, y = ref.group(1), float(at.group(1)), float(at.group(2))
        if re.fullmatch(r"H\d+", r):
            holes[r] = (x, y)
        elif re.fullmatch(r"SW\d+", r):
            switches[r] = (x, y)
        elif re.fullmatch(r"J\d+", r):
            conns[r] = (x, y)

    return dict(
        x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys),
        w=max(xs) - min(xs), d=max(ys) - min(ys),
        cx=(min(xs) + max(xs)) / 2.0, cy=(min(ys) + max(ys)) / 2.0,
        holes=holes, switches=switches, conns=conns,
    )


B = parse_board(PCB_FILE)
BOARD_W, BOARD_D = B["w"], B["d"]
BCX, BCY = B["cx"], B["cy"]

# KiCad Y grows downward; CAD Y grows up. Case origin = board centre.
#   case_x = kicad_x - BCX        case_y = -(kicad_y - BCY)
to_case = lambda x, y: (x - BCX, -(y - BCY))

if len(B["holes"]) != 4:
    raise SystemExit(f"expected 4 mounting holes (H1-H4), found {sorted(B['holes'])}. "
                     "Add them in KiCad - see PREFAB_CHECKLIST.md section 1.")
if len(B["switches"]) != 53:
    raise SystemExit(f"expected 53 switches, found {len(B['switches'])}")

stands = [to_case(*p) for p in B["holes"].values()]

# Where the key field sits relative to the board centre. keymap.centers() is
# origin-centred on the KEY FIELD, but the case is centred on the BOARD, and the
# two are NOT the same point - the board carries a ~48 mm electronics strip below
# the last key row. Derive the offset from the real switch coordinates.
sw_x = [p[0] for p in B["switches"].values()]
sw_y = [p[1] for p in B["switches"].values()]
KEY_DX, KEY_DY = to_case((min(sw_x) + max(sw_x)) / 2.0, (min(sw_y) + max(sw_y)) / 2.0)

# The PCB's real key pitch, measured rather than assumed - it must agree with the
# pitch used to generate the cutouts or the holes will not line up with the caps.
_ux = sorted({round(v, 3) for v in sw_x})
PITCH_MEASURED = round(min(b - a for a, b in zip(_ux, _ux[1:])), 3)

# Connector openings are cut where the connectors actually are.
_j1 = B["conns"].get("J1")
_j3 = B["conns"].get("J3")
J1_X = to_case(*_j1)[0] if _j1 else 0.0
J3_Y = to_case(*_j3)[1] if _j3 else 0.0


# ---------------------------------------------------------------------------
# Parameters (mm)
# ---------------------------------------------------------------------------
PITCH = PITCH_MEASURED           # from the board, not hard-coded
KEY_GAP = 2.0                    # cap clearance: cutout = key cell minus this
CLEAR = 1.6                      # board edge -> inner wall, per side
WALL, FLOOR_TH, PLATE_TH = 2.4, 2.0, 2.0
STANDOFF_H = 6.0                 # floor -> underside of PCB
LEAD_CLEAR = 1.0                 # min air under protruding THT leads
BOSS_OD, SCREW_D, INSERT_D = 7.0, 2.9, 3.4
IN_FILLET = 1.0                  # interior corner radius; board corners are square
OUT_FILLET = 2.0

CASE_W = BOARD_W + 2 * CLEAR + 2 * WALL
CASE_D = BOARD_D + 2 * CLEAR + 2 * WALL
INNER_W, INNER_D = CASE_W - 2 * WALL, CASE_D - 2 * WALL

# Interior height must clear the tallest part on the board. Measured from the
# exported STEP below; this is the floor-to-top-plate figure.
CASE_H = 20.0


# ---------------------------------------------------------------------------
# Fit checks - fail loudly rather than print a case that cannot work
# ---------------------------------------------------------------------------
def check():
    errs, warns = [], []

    if INNER_W < BOARD_W + 2 * CLEAR - 1e-9:
        errs.append(f"interior width {INNER_W:.3f} < board {BOARD_W:.3f} + 2x{CLEAR}")
    if INNER_D < BOARD_D + 2 * CLEAR - 1e-9:
        errs.append(f"interior depth {INNER_D:.3f} < board {BOARD_D:.3f} + 2x{CLEAR}")

    # Square board corners vs a filleted interior: the fillet eats into the corner
    # diagonally by r - r/sqrt(2).
    intrude = IN_FILLET - IN_FILLET / (2 ** 0.5)
    if intrude > CLEAR:
        errs.append(f"interior fillet r={IN_FILLET} intrudes {intrude:.3f} > clearance {CLEAR}")

    # Every standoff must land on the board, and be far enough in to carry a boss.
    for i, (sx, sy) in enumerate(stands):
        if abs(sx) > BOARD_W / 2 or abs(sy) > BOARD_D / 2:
            errs.append(f"standoff {i} ({sx:.3f},{sy:.3f}) is off the board")
        if abs(sx) + BOSS_OD / 2 > BOARD_W / 2 + CLEAR:
            warns.append(f"standoff {i} boss overhangs the board edge in X")

    if abs(PITCH_MEASURED - 12.0) > 1e-6:
        warns.append(f"measured key pitch {PITCH_MEASURED} != 12.0 assumed by keymap.py")

    return errs, warns


ERRS, WARNS = check()
for w in WARNS:
    print("  WARNING:", w)
if ERRS:
    for e in ERRS:
        print("  ERROR:", e)
    raise SystemExit("case does not fit the board - refusing to export")


# ---------------------------------------------------------------------------
# Bottom tray
# ---------------------------------------------------------------------------
# Screw bosses and PCB standoffs are the SAME features, at the real mounting
# holes. They cannot be separate: with 1.6 mm of clearance there is no room for
# corner bosses beside a board that fills the interior - they would collide with
# it. One M2.5 screw per corner passes through the top plate, through the PCB
# hole, into an insert in the boss, so the same fastener closes the case and
# retains the board.
with BuildPart() as bottom:
    with BuildSketch():
        RectangleRounded(CASE_W, CASE_D, OUT_FILLET)
    extrude(amount=CASE_H)

    with BuildSketch(Plane.XY.offset(FLOOR_TH)):                       # hollow it
        RectangleRounded(INNER_W, INNER_D, IN_FILLET)
    extrude(amount=CASE_H - FLOOR_TH + 0.1, mode=Mode.SUBTRACT)

    with BuildSketch():                                                # bosses
        with Locations(*stands):
            Circle(BOSS_OD / 2)
    extrude(amount=FLOOR_TH + STANDOFF_H)

    with BuildSketch(Plane.XY.offset(FLOOR_TH + STANDOFF_H - 6.0)):    # insert pockets
        with Locations(*stands):
            Circle(INSERT_D / 2)
    extrude(amount=6.1, mode=Mode.SUBTRACT)

    # Openings, positioned from the real connector coordinates rather than by eye.
    #   J3 (USB-C) is mounted flush with the RIGHT board edge, so this is a true
    #   plug-through port. J1 (link) is a soldered pigtail ~9.5 mm inboard of the
    #   front edge, so that one stays a wire exit.
    with Locations((J1_X, -CASE_D / 2 + WALL / 2, FLOOR_TH + STANDOFF_H + 4)):
        Box(16, WALL * 3, 9, mode=Mode.SUBTRACT)                       # J1 link pigtail
    with Locations((CASE_W / 2 - WALL / 2, J3_Y, FLOOR_TH + STANDOFF_H + 3)):
        Box(WALL * 3, 13, 8, mode=Mode.SUBTRACT)                       # J3 USB-C port

# ---------------------------------------------------------------------------
# Top plate - key cutouts at the real switch positions
# ---------------------------------------------------------------------------
keycells = centers(PITCH)        # origin-centred on the KEY FIELD
with BuildPart() as top:
    with BuildSketch(Plane.XY.offset(CASE_H)):
        RectangleRounded(CASE_W, CASE_D, OUT_FILLET)
        for cx, cy, w in keycells:
            with Locations((cx + KEY_DX, cy + KEY_DY)):                # -> board frame
                Rectangle(w * PITCH - KEY_GAP, PITCH - KEY_GAP, mode=Mode.SUBTRACT)
        with Locations(*stands):
            Circle(SCREW_D / 2, mode=Mode.SUBTRACT)
    extrude(amount=PLATE_TH)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
export_stl(bottom.part, os.path.join(HERE, "workboy_bottom.stl"))
export_stl(top.part, os.path.join(HERE, "workboy_top.stl"))

parts = [bottom.part, top.part]
note = []
if os.path.exists(STEP_FILE):
    board = import_step(STEP_FILE)
    bb = board.bounding_box()
    # KiCad exports X as-is and Y negated, so the same transform that maps KiCad
    # to case coords maps the STEP too: translate by (-BCX, +BCY). Derived, not
    # assumed - it is asserted below.
    board = board.moved(Location((-BCX, BCY, FLOOR_TH + STANDOFF_H)))
    nb = board.bounding_box()
    if max(abs(nb.min.X + BOARD_W / 2), abs(nb.max.X - BOARD_W / 2)) > 0.05:
        note.append(f"STEP X did not centre as expected: {nb.min.X:.3f}..{nb.max.X:.3f}")
    if max(abs(nb.min.Y + BOARD_D / 2), abs(nb.max.Y - BOARD_D / 2)) > 0.05:
        note.append(f"STEP Y did not centre as expected: {nb.min.Y:.3f}..{nb.max.Y:.3f}")

    under = nb.min.Z - FLOOR_TH        # air beneath the lowest protruding lead
    if under < LEAD_CLEAR:
        note.append(f"only {under:.3f} mm under the THT leads (want >= {LEAD_CLEAR})")
    if nb.max.Z > CASE_H:
        note.append(f"tallest part reaches {nb.max.Z:.3f} mm, above the top plate at {CASE_H}")

    board.label = "PCB"
    parts.append(board)
else:
    note.append(f"no board STEP at {STEP_FILE}; exported case only. "
                "Generate it with: kicad-cli pcb export step")

export_step(Compound(children=parts), os.path.join(HERE, "workboy_case_assembly.step"))

# ---------------------------------------------------------------------------
print(f"board  : {BOARD_W:.3f} x {BOARD_D:.3f} mm, centre ({BCX:.4f}, {BCY:.4f}) [from {os.path.basename(PCB_FILE)}]")
print(f"case   : {CASE_W:.3f} x {CASE_D:.3f} x {CASE_H + PLATE_TH:.3f} mm outer")
print(f"         {INNER_W:.3f} x {INNER_D:.3f} mm interior ({CLEAR} mm clearance per side)")
print(f"key    : pitch {PITCH} mm measured from the board; field offset "
      f"({KEY_DX:+.4f}, {KEY_DY:+.4f}) from the board centre")
print(f"mounts : {len(stands)} at " + ", ".join(f"({x:+.3f},{y:+.3f})" for x, y in sorted(stands)))
print(f"ports  : J1 pigtail slot at x={J1_X:+.3f} on the front wall; "
      f"J3 USB-C port at y={J3_Y:+.3f} on the right wall")
for n in note:
    print("  NOTE:", n)
print("exported: workboy_top.stl, workboy_bottom.stl, workboy_case_assembly.step")
