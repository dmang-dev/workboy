# WorkBoy PCB — layout pipeline (netlist → placed board → Gerbers/CPL)

Everything here is generated from the single-source keymap + the netlist, with
KiCad 10's `pcbnew` Python API and `kicad-cli`. The switches land at the real
[`layout/keymap.py`](../layout/keymap.py) positions.

## Files
| File | What | How |
|---|---|---|
| `workboy.net` | netlist (131 comps / 89 nets) | `python generate_workboy_netlist.py` |
| `key_positions.json` | per-switch placement (mm) | `python ../layout/gen_layout.py` |
| `gen_pcb.py` | places all 131 footprints + nets + outline | KiCad-python |
| `workboy.kicad_pcb` | the board (placed; routed after SES import) | output of `gen_pcb.py` |
| `workboy.dsn` | Specctra DSN for autorouting | `pcbnew.ExportSpecctraDSN` |
| `apply_ses.py` | import Freerouting `.ses` → routed board | KiCad-python |
| `make_cpl.py` | CPL → JLCPCB format | system python |
| `workboy_cpl_jlcpcb.csv` | **CPL: Designator, Mid X, Mid Y, Rotation, Layer** | output of `make_cpl.py` |
| `gerber/` | Gerbers + drill (RS-274X) | `kicad-cli pcb export gerbers/drill` |

## Regenerate from scratch
```powershell
$K = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin"
# 1. netlist + placement inputs
python generate_workboy_netlist.py
python ..\layout\gen_layout.py
# 2. place the board
& "$K\python.exe" gen_pcb.py
# 3. export DSN, autoroute, import back
& "$K\python.exe" -c "import pcbnew; b=pcbnew.LoadBoard('workboy.kicad_pcb'); pcbnew.ExportSpecctraDSN(b,'workboy.dsn')"
# Freerouting 2.2.4 needs Java 25 (class file 69); 1.9.0 still runs on Java 17.
& "$env:ProgramFiles\Eclipse Adoptium\jdk-25.0.4.7-hotspot\bin\java.exe" `
    -Djava.awt.headless=true -jar ..\tools\freerouting.jar `
    -de workboy.dsn -do workboy.ses -mp 20
& "$K\python.exe" apply_ses.py
# 4. fab outputs
& "$K\kicad-cli.exe" pcb export gerbers -o gerber workboy.kicad_pcb
& "$K\kicad-cli.exe" pcb export drill   -o gerber workboy.kicad_pcb
& "$K\kicad-cli.exe" pcb export pos --format csv --units mm --side both -o cpl_raw.csv workboy.kicad_pcb
python make_cpl.py
```

## Submitting to JLCPCB
1. Zip the `gerber/` folder → upload as the Gerbers.
2. BOM = [`../workboy_jlcpcb_bom.csv`](../workboy_jlcpcb_bom.csv).
3. CPL = `workboy_cpl_jlcpcb.csv`.
4. The link connector **J1** is consigned/cut-cable (not in the BOM) — exclude it
   from assembly. Re-verify the **J3 USB-C** footprint vs the real C165948 part.

## Status: DRC-CLEAN ✅
`kicad-cli pcb drc --severity-all` reports **0 violations, 0 unconnected, 0 footprint
errors** on the routed board (2-layer, **152.000 × 106.125 mm**, 135 footprints,
1011 track/via objects). Diodes sit in the inter-row gap (clear of the switch
courtyards). Design rules: 0.25 mm tracks, **0.15 mm clearance** (JLCPCB 6-mil
standard), 0.6/0.3 mm vias. The Gerbers in `gerber/` (zipped as
`workboy_gerbers.zip`) are ready to fab.

### Placement notes (2026-07-28)
- **The outline is pinned**, not derived. It used to be the bounding box of every
  placed part + 10 mm, so moving one component silently resized the board — and the
  size is load-bearing for the case, the mounting holes and the quote. `BX0..BY1` in
  `gen_pcb.py` fix it; placement is asserted to fit inside and the script refuses to
  write a board that overflows.
- **J3 is placed explicitly, flush with the right edge** (rot 90, mating face
  outward) so a USB-C plug can reach it. It previously landed wherever the
  support-part flow put it, ~16 mm inside the outline.
- **R10/R11/D54 are placed explicitly beside J3.** The row-wrapping flow used to
  strand R11 and D54 ~130 mm away, dragging VBUS across the whole board; that run is
  now 13.7 mm.
- **H1–H4 mounting holes** are placed at a 4.0 mm corner inset, excluded from the BOM
  and position file, with their reference labels on `F.Fab` (at 4 mm the silkscreen
  text is clipped by the outline and trips `silk_edge_clearance`).

> ⚠️ **`gen_pcb.py` ordering is load-bearing.** Mutating footprints
> (`Remove`/`SetAttributes`) invalidates KiCad 10's SWIG proxies, so every such call
> must come *after* the last `FootprintLoad` **and** after the `fp.Pads()`
> net-assignment loop. Doing it earlier fails with `'SwigPyObject' object has no
> attribute 'FootprintLoad'` or `'SwigPyObject' object is not iterable`.

> ⚠️ **Export the DSN from an *unrouted* board.** `gen_pcb.py` writes a placed,
> unrouted board; exporting a DSN from an already-routed one makes Freerouting
> re-route on top of existing copper and leave nets unrouted. Assert
> `len(board.GetTracks()) == 0` before exporting.

## Before ordering — quick sanity
- **J3 USB-C is the real C165948** — Korean Hroparts `TYPE-C-31-M-12`, official KiCad
  footprint `USB_C_Receptacle_HRO_TYPE-C-31-M-12`. Pinout verified (VBUS=A4/A9/B4/B9,
  GND=A1/A12/B1/B12, CC1=A5, CC2=B5, shield=SH); re-DRC = 0 violations. ✅
- Hand-solder J1 (link pigtail) and the 53 switches; J1 is consigned (not in the BOM).
- 2-layer, no controlled impedance needed (8 kHz link); default JLCPCB stackup is fine.
- A human glance over the autorouted traces before a production run never hurts.
