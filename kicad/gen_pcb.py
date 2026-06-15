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
          ["R7", "LED1"], ["R8", "LED2"], ["R9", "LED3"],
          ["J3", "R10", "R11", "D54"]]
order = []
for g in GROUPS:
    order += g
order += [r for r in comp_fp if r not in order]
order = [r for r in order if r in comp_fp and r not in placed]   # skip switches/diodes

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

# ---- board outline (bbox of all placed parts + margin) --------------------
allx = [pcbnew.ToMM(fp.GetPosition().x) for fp in placed.values()]
ally = [pcbnew.ToMM(fp.GetPosition().y) for fp in placed.values()]
m = 10                            # outline margin (room for routing, off the edge)
x0, x1, y0, y1 = min(allx) - m, max(allx) + m, min(ally) - m, max(ally) + m
for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(mm(a)); seg.SetEnd(mm(b))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(pcbnew.FromMM(0.15))
    board.Add(seg)

pcbnew.SaveBoard(OUT, board)
print(f"placed {len(placed)}/{len(comp_fp)} components; board {x1-x0:.0f} x {y1-y0:.0f} mm")
if missing:
    print("MISSING footprints (skipped):", missing)
print("wrote", OUT)
