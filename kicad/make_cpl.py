#!/usr/bin/env python3
"""Convert KiCad's cpl_raw.csv (kicad-cli pcb export pos) to JLCPCB CPL format:
   Designator, Mid X, Mid Y, Rotation, Layer."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, "cpl_raw.csv")
dst = os.path.join(HERE, "workboy_cpl_jlcpcb.csv")
rows = list(csv.DictReader(open(src)))
with open(dst, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Rotation", "Layer"])
    for r in rows:
        layer = "Top" if r["Side"].lower().startswith("t") else "Bottom"
        w.writerow([r["Ref"], r["PosX"], r["PosY"], r["Rot"], layer])
print("wrote", os.path.basename(dst), len(rows), "parts")
