#!/usr/bin/env python3
"""
gen_pcb.py — build a placed KiCad .kicad_pcb from workboy.net + key_positions.json.

Run with KiCad's bundled Python (it has the pcbnew module):
    "<KiCad>/bin/python.exe" gen_pcb.py

Places every component (the 53 switches at the real keymap layout, each diode by
its switch, the MCU/passives/connectors in a strip below), assigns nets from the
netlist, and draws the board outline. Routing is left to KiCad/Freerouting.
Then export Gerbers + CPL with kicad-cli (see gen_pcb_export.ps1).
"""
import os, re, json, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def _default_fplib():
    """Locate KiCad's footprint library without hardcoding a user path.
    Override with the KICAD_FP environment variable if needed."""
    env = os.environ.get("KICAD_FP")
    if env:
        return env
    cands = []
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands.append(os.path.join(la, "Programs", "KiCad", "10.0", "share", "kicad", "footprints"))
    cands += [r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
              "/usr/share/kicad/footprints",
              "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"]
    for c in cands:
        if c and os.path.isdir(c):
            return c
    return cands[0] if cands else ""


FPLIB = _default_fplib()
NET = os.path.join(HERE, "workboy.net")
POS = os.path.join(HERE, "key_positions.json")
OUT = os.path.join(HERE, "workboy.kicad_pcb")

OX, OY = 150.0, 70.0          # board-space centre of the key field (mm)

# ---- board outline: PINNED, not derived -----------------------------------
# This used to be the bounding box of every placed part + 10 mm, which meant
# moving any single component silently resized the board. The size is
# load-bearing - the case, the mounting-hole positions and the JLCPCB quote all
# depend on it - so it is fixed here at the verified rev A dimensions and the
# placement is asserted to fit inside it instead.
BX0, BX1, BY0, BY1 = 74.0, 226.0, 36.0, 142.125          # 152.000 x 106.125 mm

# J3 sits flush with the RIGHT edge so a USB-C plug can actually reach it. It
# used to land wherever the support-part flow happened to put it, ~16 mm inside
# the outline, where no plug could reach. Rotation 90 turns the footprint's
# mating face (local +Y) toward +X - verified by measuring the courtyard, not
# assumed. The body (F.Fab) is +/-3.650 mm, so the front face lands exactly on
# the edge; the courtyard overhangs it by 0.545 mm, which is normal for an
# edge-mounted connector.
J3_ROT = 90
J3_BODY_HALF = 3.650
J3_POS = (BX1 - J3_BODY_HALF, 114.755)

# J3's support parts, kept beside it. The flow placement used to wrap rows and
# strand R11 and D54 ~130 mm away on the far side of the board, which is why
# VBUS ran the full width of the PCB.
CLUSTER_POS = {
    "D54": (210.0, 114.755),      # VBUS -> +5V Schottky (SMA)
    "R10": (214.0, 110.500),      # CC1 pulldown 5.1k
    "R11": (214.0, 119.000),      # CC2 pulldown 5.1k
}

# Mounting holes, 4.0 mm in from each corner. Chosen by scanning clearance
# against every pad, track, via and part body; 4.0 mm maximises clearance at the
# tightest corner (H2 vs SW12). See PREFAB_CHECKLIST.md section 1.
HOLE_INSET = 4.0


def mm(v):
    return pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1]))


# ---- parse the netlist ----------------------------------------------------
txt = open(NET, encoding="utf-8").read()
comps = re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]+)"\)', txt)
comp_fp = {ref: (val, fp) for ref, val, fp in comps}

nets = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)((?:\s*\(node \(ref "[^"]+"\) \(pin "[^"]+"\)\))*)', txt):
    name = m.group(1)
    nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)\)', m.group(2))
    nets[name] = nodes

# ---- key positions --------------------------------------------------------
kp = json.load(open(POS, encoding="utf-8"))
sw_pos = {k["ref"]: (k["x"], k["y"]) for k in kp["keys"]}   # SWn -> (cx, cy) keymap mm

# ---- board + footprints ---------------------------------------------------
board = pcbnew.CreateEmptyBoard()

# --- design rules so the autorouter produces DRC-clean copper ---
ds = board.GetDesignSettings()
ds.m_MinClearance = pcbnew.FromMM(0.15)     # JLCPCB 6-mil standard; clears USB-C pitch
ds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
ds.m_SolderMaskMinWidth = 0                 # waive mask slivers between fine-pitch pads
_nc = ds.m_NetSettings.GetDefaultNetclass()
for _setter, _val in [("SetClearance", 0.15), ("SetTrackWidth", 0.25),
                      ("SetViaDiameter", 0.6), ("SetViaDrill", 0.3)]:
    try:
        getattr(_nc, _setter)(pcbnew.FromMM(_val))
    except Exception as _e:
        print("  netclass", _setter, "skipped:", _e)

placed, missing = {}, []


def load_fp(ref):
    val, fpid = comp_fp[ref]
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)
    if fp is None:
        missing.append((ref, fpid))
        return None
    fp.SetReference(ref)
    fp.SetValue(val)
    board.Add(fp)
    placed[ref] = fp
    return fp


def place(ref, x, y):
    fp = load_fp(ref)
    if fp:
        fp.SetPosition(mm((x, y)))
    return fp


# switches at the keymap layout (flip keymap +y-up to KiCad +y-down)
for ref, (cx, cy) in sw_pos.items():
    place(ref, OX + cx, OY - cy)
# diodes by their switch (Dn shares index with SWn)
for ref in [r for r in comp_fp if r.startswith("D") and r[1:].isdigit() and int(r[1:]) <= 53]:
    sw = "SW" + ref[1:]
    if sw in sw_pos:
        cx, cy = sw_pos[sw]
        place(ref, OX + cx, OY - cy + 8.25)   # gap centre (switch crtyd runs +6mm down)

# support parts: grouped by connectivity (short local routes), size-aware spacing
xs = [OX + sw_pos[s][0] for s in sw_pos]
ys = [OY - sw_pos[s][1] for s in sw_pos]
minx, maxx, maxy = min(xs), max(xs), max(ys)
GROUPS = [["U1"], ["C1", "C2", "C5"], ["C3", "C4", "C6"], ["R1", "R2", "R3"],
          ["J1", "R4", "R5", "R6"], ["J2"],
          ["R7", "LED1"], ["R8", "LED2"], ["R9", "LED3"]]
# J3's cluster and the mounting holes are placed EXPLICITLY below, not by the
# flow. They were last in the flow order, so removing them shifts nothing else.
EXPLICIT = ["J3"] + list(CLUSTER_POS) + ["H1", "H2", "H3", "H4"]
order = []
for g in GROUPS:
    order += g
order += [r for r in comp_fp if r not in order]
order = [r for r in order if r in comp_fp and r not in placed and r not in EXPLICIT]

def crt_wh(fp):
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())

x_left, x_right = minx, maxx
gx, gy, row_h = x_left, maxy + 16, 0.0
for ref in order:
    fp = load_fp(ref)
    if not fp:
        continue
    w, h = crt_wh(fp)
    if gx + w > x_right:                 # wrap to next row
        gx = x_left
        gy += row_h + 4
        row_h = 0.0
    fp.SetPosition(mm((gx + w / 2.0, gy + h / 2.0)))
    gx += w + 2.5
    row_h = max(row_h, h)

# ---- explicit placement: J3 at the edge, its cluster, the mounting holes ----
# NOTE: only load + position here. Mutating a footprint (Remove/SetAttributes)
# in between FootprintLoad calls invalidates KiCad's cached IO-plugin proxy and
# the next load dies with "'SwigPyObject' object has no attribute
# 'FootprintLoad'". All post-processing happens after the last load, below.
_j3 = place("J3", *J3_POS)
if _j3:
    _j3.SetOrientationDegrees(J3_ROT)
for _ref, _xy in CLUSTER_POS.items():
    place(_ref, *_xy)
for _ref, _sx, _sy in (("H1", BX0, BY0), ("H2", BX1, BY0),
                       ("H3", BX0, BY1), ("H4", BX1, BY1)):
    place(_ref,
          _sx + (HOLE_INSET if _sx == BX0 else -HOLE_INSET),
          _sy + (HOLE_INSET if _sy == BY0 else -HOLE_INSET))

# ---- nets -----------------------------------------------------------------
netinfo = {}
for name in nets:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    netinfo[name] = ni
for name, nodes in nets.items():
    ni = netinfo[name]
    for ref, pin in nodes:
        fp = placed.get(ref)
        if not fp:
            continue
        for pad in fp.Pads():
            if pad.GetNumber() == pin:
                pad.SetNet(ni)

# ---- board outline (PINNED - see BX0..BY1 at the top) ---------------------
x0, x1, y0, y1 = BX0, BX1, BY0, BY1

# Everything except J3 must sit inside the outline. J3 is deliberately flush with
# the right edge, so its courtyard overhangs and is exempt.
_bad = []
for _ref, _fp in placed.items():
    if _ref == "J3":
        continue
    _bb = _fp.GetBoundingBox(False, False)
    if (pcbnew.ToMM(_bb.GetLeft()) < x0 or pcbnew.ToMM(_bb.GetRight()) > x1 or
            pcbnew.ToMM(_bb.GetTop()) < y0 or pcbnew.ToMM(_bb.GetBottom()) > y1):
        _bad.append(_ref)
if _bad:
    raise SystemExit(f"placement overflows the pinned outline: {sorted(_bad)}. "
                     "Widen BX0..BY1 deliberately (it changes the case and the quote) "
                     "or fix the placement.")

for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(mm(a)); seg.SetEnd(mm(b))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(pcbnew.FromMM(0.15))
    board.Add(seg)

# ---- post-processing: MUST come last -------------------------------------
# Mutating footprints (Remove / SetAttributes) invalidates KiCad 10's SWIG
# proxies, so anything that still needs to read footprints - FootprintLoad, and
# the fp.Pads() net-assignment loop above - has to happen first. Doing this
# earlier fails with "'SwigPyObject' object is not iterable".
#
# J3 is flush with the edge, so part of its silkscreen falls past the outline.
# Fabs clip that automatically, but it trips silk_edge_clearance and this board
# is kept at zero DRC violations, so drop the segments that cross the edge.
if _j3:
    for _g in list(_j3.GraphicalItems()):
        if _g.GetLayer() == pcbnew.F_SilkS and \
                pcbnew.ToMM(_g.GetBoundingBox().GetRight()) > BX1 - 0.2:
            _j3.Remove(_g)

for _ref in ("H1", "H2", "H3", "H4"):
    _h = placed.get(_ref)
    if not _h:
        continue
    try:                     # keep them out of the BOM and the position file
        _h.SetAttributes(_h.GetAttributes()
                         | pcbnew.FP_EXCLUDE_FROM_BOM
                         | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    except Exception as _e:
        print("  hole attributes skipped:", _e)

pcbnew.SaveBoard(OUT, board)

# ---- post-save text fixup --------------------------------------------------
# The mounting holes sit 4 mm from the outline, which leaves no room for their
# reference text on the silkscreen - DRC flags it as silk_edge_clearance. Move
# those labels to F.Fab, which is not subject to the silk-edge rule and is where
# a hole's designator belongs anyway.
#
# Done as a text edit because footprint FIELDS cannot be reached from KiCad 10's
# Python bindings: fp.Reference() comes back as a bare SwigPyObject with no
# SetVisible/SetLayer. Scoped strictly to the H1-H4 blocks.
_src = open(OUT, encoding="utf-8").read()
_n = 0


def _retarget_ref_layer(text, ref):
    """Put <ref>'s Reference field on F.Fab instead of F.SilkS."""
    global _n
    i = text.find(f'(property "Reference" "{ref}"')
    if i < 0:
        return text
    j = text.find(")", text.find('(layer "F.SilkS")', i)) if \
        text.find('(layer "F.SilkS")', i, i + 400) > 0 else -1
    k = text.find('(layer "F.SilkS")', i, i + 400)
    if k < 0:
        return text
    _n += 1
    return text[:k] + '(layer "F.Fab")' + text[k + len('(layer "F.SilkS")'):]


for _ref in ("H1", "H2", "H3", "H4"):
    _src = _retarget_ref_layer(_src, _ref)
if _n:
    open(OUT, "w", encoding="utf-8", newline="\n").write(_src)
print(f"  moved {_n} mounting-hole reference labels to F.Fab")

print(f"placed {len(placed)}/{len(comp_fp)} components; board {x1-x0:.0f} x {y1-y0:.0f} mm")
if missing:
    print("MISSING footprints (skipped):", missing)
print("wrote", OUT)
