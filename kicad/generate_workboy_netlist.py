#!/usr/bin/env python3
"""
generate_workboy_netlist.py
---------------------------------------------------------------------------
Emits a KiCad netlist (.net, "export version E") for the WorkBoy keyboard
controller PCB described in C:\\workboy\\BUILD_PLAN.md (section 3).

Pure standard-library Python (no deps). Import the resulting workboy.net into
KiCad's PCB editor:  File > Import > Netlist...  (KiCad 7/8), then lay out the
board and generate Gerbers + the CPL/centroid for JLCPCB.

Design: ATmega328P-AU @ 5V (no level shifter), 8x7 diode matrix (53 keys),
USB-C 5V power, GB link via 220R series, ISP header, 3 status LEDs.
See WORKBOY_PROTOCOL.md for the scan-code map and firmware/workboy_keyboard.c
for the matching SCANCODE[ROWS][COLS] table.

NOTE: footprint refs use standard KiCad libraries. Two need verifying against
the exact JLCPCB parts: J3 (USB-C C165948 pad map) and J1 (the GB EXT link
connector, which has no catalog footprint -- cut-cable pigtail / breakout).
"""
import os, sys
from collections import defaultdict, OrderedDict

# ----- design metadata -----------------------------------------------------
SOURCE = "generate_workboy_netlist.py"
DATE   = "2026-06-14"

# ----- 8x7 matrix from the single source of truth (layout/keymap.py) --------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "layout"))
import keymap as _km
SCAN = _km.scancode_grid()       # 0x00 = unpopulated cell. 53 populated.
ROWS, COLS = _km.ROWS, _km.COLS

# ----- footprint library refs ----------------------------------------------
FP_MCU   = "Package_QFP:TQFP-32_7x7mm_P0.8mm"
FP_R     = "Resistor_SMD:R_0402_1005Metric"
FP_C0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_DIODE = "Diode_SMD:D_SOD-123"          # pad1=cathode(K), pad2=anode(A)
FP_SS14  = "Diode_SMD:D_SMA"              # pad1=cathode, pad2=anode
FP_LED   = "LED_SMD:LED_0805_2012Metric"  # pad1=cathode, pad2=anode
FP_SW    = "Button_Switch_THT:SW_PUSH_6mm"
FP_ISP   = "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical"
FP_USBC  = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"  # = LCSC C165948
FP_LINK  = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"  # link pigtail
FP_MOUNT = "MountingHole:MountingHole_2.7mm_M2.5"   # plain NPTH, no copper

# J4 - REAL GAME BOY EXT SOCKET. *** DEFERRED TO REV B (decided 2026-07-28). ***
#
# The OPTIONAL alternative to J1: an ordinary link cable plugs in instead of a
# soldered pigtail. Both land on the SAME nets and only one is ever populated.
#
# Why not in rev A: there is no KiCad library footprint for this part, and one
# cannot be drawn without the physical connector in hand to measure (it IS
# purchasable as a repair part - see COMPATIBILITY.md). Drawing it, re-importing,
# re-placing, re-routing and re-exporting was the entire remaining critical path
# for rev A, in exchange for cable convenience over a pigtail that works on day
# one. Rev A proves the design; rev B can add the socket, measured against a board
# that by then exists.
#
# The reference below points at a deliberately NON-EXISTENT library so that if
# anyone flips the flag before drawing the footprint, KiCad fails loudly on import
# rather than silently substituting a wrong land pattern.
FP_LINK_SOCKET  = "workboy:GB_EXT_Socket_6P"
EMIT_LINK_SOCKET = False   # rev A = J1 only; flip to True only AFTER drawing the footprint

# J5 - BOARD-EDGE TONGUE. *** DECIDED AGAINST for rev A (2026-07-28). ***
# Kept here, inert, because the analysis is worth not repeating.
#
# The idea: shape the board edge itself into the link plug - a ~6 mm tongue with
# 3 pads top and 3 bottom, inserted straight into the console's link socket. Zero
# parts. Unlike J1/J4 it is NOT free:
#   * changes the board OUTLINE, so the case must be re-fitted around it
#   * an inserted/removed edge wants ENIG (~1.5-2.0x the bare-board line vs HASL),
#     or the pads wear; hard "gold fingers" is ~3.0-5.0x and overkill here
#   * the socket is nominally ~1.2 mm, so a standard 1.6 mm board is a tight fit
#     (1.6 mm is JLCPCB's free default - thickness is a FIT issue, not a cost one)
#   * it plugs the board DIRECTLY into the console: rigid, no cable. Fine for a
#     compact variant, wrong for a keyboard you sit and type on - which is the
#     whole point of this device.
# If ever revisited: put the tongue on a break-off tab (mouse-bites / V-score) so
# one fab run yields both variants, and order ENIG - skip hard gold.
FP_LINK_EDGE  = "workboy:GB_EXT_EdgeTongue_6P"
EMIT_LINK_EDGE = False   # parked - see above; leave False

# ----- accumulators --------------------------------------------------------
comps = OrderedDict()                 # ref -> (value, footprint, lcsc)
nets  = defaultdict(list)             # netname -> [(ref, pin), ...]

def add_comp(ref, value, fp, lcsc=""):
    comps[ref] = (value, fp, lcsc)

def n(name, *nodes):                  # connect pins to a net
    for ref, pin in nodes:
        nets[name].append((ref, str(pin)))

# ===========================================================================
# U1  ATmega328P-AU  (TQFP-32 pin -> net)
# ===========================================================================
add_comp("U1", "ATmega328P-AU", FP_MCU, "C14877")
U1 = {
    1:"ROW3", 2:"ROW4", 3:"GND", 4:"+5V", 5:"GND", 6:"+5V",
    7:"NET_PB6", 8:"NET_PB7", 9:"ROW5", 10:"ROW6", 11:"ROW7",
    12:"COL6", 13:None, 14:"nSS", 15:"MCU_MOSI", 16:"MCU_MISO", 17:"MCU_SCK",
    18:"+5V", 19:None, 20:"AREF", 21:"GND", 22:None,
    23:"COL0", 24:"COL1", 25:"COL2", 26:"COL3", 27:"COL4", 28:"COL5",
    29:"nRESET", 30:"ROW0", 31:"ROW1", 32:"ROW2",
}
for pin, net in U1.items():
    if net:
        nets[net].append(("U1", str(pin)))

# ===========================================================================
# Decoupling / bulk
# ===========================================================================
for ref in ("C1", "C2", "C3"):
    add_comp(ref, "100nF", FP_C0402, "C1525"); n("+5V", (ref,1)); n("GND", (ref,2))
add_comp("C4", "100nF", FP_C0402, "C1525"); n("AREF", ("C4",1)); n("GND", ("C4",2))
for ref in ("C5", "C6"):
    add_comp(ref, "10uF", FP_C0805, "C15850"); n("+5V", (ref,1)); n("GND", (ref,2))

# ===========================================================================
# Resistors
# ===========================================================================
add_comp("R1", "10k",  FP_R, "C25744"); n("nRESET",  ("R1",1)); n("+5V", ("R1",2))   # reset pull-up
add_comp("R2", "10k",  FP_R, "C25744"); n("nSS",     ("R2",1)); n("GND", ("R2",2))   # /SS strap low
add_comp("R3", "10k",  FP_R, "C25744"); n("MCU_SCK", ("R3",1)); n("GND", ("R3",2))   # SCK idle low
add_comp("R4", "220",  FP_R, "C25091"); n("LINK_SI", ("R4",1)); n("MCU_MISO",("R4",2))
add_comp("R5", "220",  FP_R, "C25091"); n("LINK_SO", ("R5",1)); n("MCU_MOSI",("R5",2))
add_comp("R6", "220",  FP_R, "C25091"); n("LINK_SC", ("R6",1)); n("MCU_SCK", ("R6",2))
add_comp("R7", "1k",   FP_R, "C11702"); n("+5V",     ("R7",1)); n("LED1_A",  ("R7",2))
add_comp("R8", "1k",   FP_R, "C11702"); n("NET_PB6", ("R8",1)); n("LED2_A",  ("R8",2))
add_comp("R9", "1k",   FP_R, "C11702"); n("NET_PB7", ("R9",1)); n("LED3_A",  ("R9",2))
add_comp("R10","5.1k", FP_R, "C25905"); n("USB_CC1", ("R10",1)); n("GND", ("R10",2))
add_comp("R11","5.1k", FP_R, "C25905"); n("USB_CC2", ("R11",1)); n("GND", ("R11",2))

# ===========================================================================
# LEDs (pad1=K -> GND, pad2=A -> resistor)
# ===========================================================================
add_comp("LED1", "RED",   FP_LED, "C2286");  n("GND", ("LED1",1)); n("LED1_A", ("LED1",2))
add_comp("LED2", "GREEN", FP_LED, "C72043"); n("GND", ("LED2",1)); n("LED2_A", ("LED2",2))
add_comp("LED3", "GREEN", FP_LED, "C72043"); n("GND", ("LED3",1)); n("LED3_A", ("LED3",2))

# ===========================================================================
# D54  SS14 Schottky:  VBUS(anode,pad2) -> +5V(cathode,pad1)
# ===========================================================================
add_comp("D54", "SS14", FP_SS14, "C2480"); n("+5V", ("D54",1)); n("VBUS", ("D54",2))

# ===========================================================================
# J3  USB-C 16P power-only  (GCT pad names -- VERIFY against C165948 footprint)
# ===========================================================================
add_comp("J3", "USB-C-16P", FP_USBC, "C165948")
# C165948 = HRO TYPE-C-31-M-12 (verified pinout): VBUS=A4/A9/B4/B9, GND=A1/A12/B1/B12,
# CC1=A5, CC2=B5; shield is one tab named "SH". D+/D-/SBU unused (power-only).
for p in ("A1","B1","A12","B12","SH"): n("GND",  ("J3", p))
for p in ("A4","B4","A9","B9"):        n("VBUS", ("J3", p))
n("USB_CC1", ("J3","A5")); n("USB_CC2", ("J3","B5"))

# ===========================================================================
# J2  ISP 2x3  (shares SPI nets -- program BEFORE attaching the link cable)
# ===========================================================================
add_comp("J2", "ISP-2x3", FP_ISP, "C2718")
n("MCU_MISO",("J2",1)); n("+5V",("J2",2)); n("MCU_SCK",("J2",3))
n("MCU_MOSI",("J2",4)); n("nRESET",("J2",5)); n("GND",("J2",6))

# ===========================================================================
# J1  GB EXT link  (1=VCC NC, 2=SO, 3=SI, 4=SD NC, 5=SC, 6=GND)
#
# *** THIS IS THE LINK CONNECTOR REV A SHIPS. *** 1x6 0.1" header; attach a cut
# link cable as a pigtail. METER IT FIRST - the two ends of a link cable are
# deliberately cross-wired, and reversed SI/SO is a top failure mode.
# ===========================================================================
add_comp("J1", "GB-LINK", FP_LINK, "")
n("LINK_VCC",("J1",1)); n("LINK_SO",("J1",2)); n("LINK_SI",("J1",3))
n("LINK_SD",("J1",4));  n("LINK_SC",("J1",5)); n("GND",("J1",6))

# ===========================================================================
# J4  GB EXT socket - DEFERRED TO REV B, inert. Same nets as J1; populate ONE.
#   J1 = 0.1" header for a soldered cut-cable pigtail  <- REV A SHIPS THIS
#   J4 = real EXT socket so a normal link cable plugs in (needs a drawn footprint)
# Pin 1 (VCC) and pin 4 (SD) stay unconnected on both: the board is USB-C
# self-powered, and stock cables only carry 4 of the 6 pins.
# ===========================================================================
if EMIT_LINK_SOCKET:
    add_comp("J4", "GB-LINK-SKT", FP_LINK_SOCKET, "")
    n("LINK_VCC",("J4",1)); n("LINK_SO",("J4",2)); n("LINK_SI",("J4",3))
    n("LINK_SD",("J4",4));  n("LINK_SC",("J4",5)); n("GND",("J4",6))

# ===========================================================================
# J5  GB EXT edge tongue - OPTIONAL third option, same nets again.
# The board edge IS the plug: 3 pads top, 3 bottom, ~6 mm wide, straight into
# the console's link socket. Zero parts. See the caveats at FP_LINK_EDGE - this
# one changes the board outline and wants gold plating, so it is not free the
# way J1 and J4 are. Populate exactly ONE of J1 / J4 / J5.
# ===========================================================================
if EMIT_LINK_EDGE:
    add_comp("J5", "GB-LINK-EDGE", FP_LINK_EDGE, "")
    n("LINK_VCC",("J5",1)); n("LINK_SO",("J5",2)); n("LINK_SI",("J5",3))
    n("LINK_SD",("J5",4));  n("LINK_SC",("J5",5)); n("GND",("J5",6))

# ===========================================================================
# H1-H4  M2.5 mounting holes (added 2026-07-28)
#
# These carry NO nets - they are plain NPTH. They are listed here anyway so that
# re-importing this netlist does not DELETE them from the board: KiCad removes
# footprints it cannot find in the incoming netlist, and the holes were placed
# directly in the PCB, not via the schematic (there is no schematic - this file
# IS the source).
#
# Positions were chosen against the real board, 4.0 mm inset from the Edge.Cuts
# centreline at each corner, symmetric about the board centre (150.0, 89.0625):
#     H1 TL ( 78.000,  40.000)      H2 TR (222.000,  40.000)
#     H3 BL ( 78.000, 138.125)      H4 BR (222.000, 138.125)
#     spacing 144.000 x 98.125 mm
# Tightest clearance is H2 vs SW12 - 4.607 mm to copper, 4.475 mm to the part
# body (a 5 mm case standoff post needs 2.5 mm). DRC: 0 violations.
# They are marked exclude-from-BOM and exclude-from-position-files in the board.
# ===========================================================================
for _h in ("H1", "H2", "H3", "H4"):
    add_comp(_h, "MountingHole_M2.5", FP_MOUNT)

# ===========================================================================
# 8x7 key matrix: 53 switches + 53 diodes
#   SWk.1 -> ROWr ; SWk.2 -> K{k} ; Dk.1(K) -> K{k} ; Dk.2(A) -> COLc
# ===========================================================================
k = 0
for r in range(ROWS):
    for c in range(COLS):
        if SCAN[r][c] == 0x00:
            continue
        k += 1
        sw, di = f"SW{k}", f"D{k}"
        add_comp(sw, "TACT_6mm", FP_SW, "C720477")
        add_comp(di, "1N4148W",  FP_DIODE, "C2099")
        n(f"ROW{r}", (sw, 1))
        n(f"KEY{k}",  (sw, 2), (di, 1))   # switch <-> diode cathode
        n(f"COL{c}",  (di, 2))            # diode anode -> column
assert k == 53, f"expected 53 keys, got {k}"

# ===========================================================================
# Emit KiCad netlist
# ===========================================================================
def esc(s):
    return str(s).replace('"', r'\"')

lines = []
lines.append('(export (version "E")')
lines.append('  (design')
lines.append(f'    (source "{SOURCE}")')
lines.append(f'    (date "{DATE}")')
lines.append('    (tool "generate_workboy_netlist.py"))')

# components
lines.append('  (components')
for ref, (val, fp, lcsc) in comps.items():
    lines.append(f'    (comp (ref "{ref}")')
    lines.append(f'      (value "{esc(val)}")')
    lines.append(f'      (footprint "{esc(fp)}")')
    if lcsc:
        lines.append(f'      (property (name "LCSC") (value "{lcsc}")))')
    else:
        lines.append('      )')
lines.append('  )')

# nets (sorted; matrix nets grouped naturally)
def net_sort_key(name):
    order = {"+5V":0, "GND":1, "VBUS":2}
    return (order.get(name, 50), name)

lines.append('  (nets')
for i, name in enumerate(sorted(nets.keys(), key=net_sort_key), start=1):
    lines.append(f'    (net (code "{i}") (name "{esc(name)}")')
    for ref, pin in nets[name]:
        lines.append(f'      (node (ref "{ref}") (pin "{pin}"))')
    lines.append('    )')
lines.append('  )')
lines.append(')')

out = "\n".join(lines) + "\n"
with open("workboy.net", "w", encoding="utf-8") as f:
    f.write(out)

# ----- summary -------------------------------------------------------------
ncomp = len(comps)
nnet  = len(nets)
npin  = sum(len(v) for v in nets.values())
kinds = defaultdict(int)
for ref in comps:
    kinds[''.join(ch for ch in ref if not ch.isdigit())] += 1
print(f"wrote workboy.net")
print(f"  components : {ncomp}  ({dict(sorted(kinds.items()))})")
print(f"  nets       : {nnet}")
print(f"  pin nodes  : {npin}")
# single-node nets are usually a wiring error (except intentional NC)
singles = [k for k,v in nets.items() if len(v) == 1]
print(f"  single-node nets (verify; NC pins ok): {singles}")
