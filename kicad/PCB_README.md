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
java -jar ..\tools\freerouting-1.9.0.jar -de workboy.dsn -do workboy.ses -mp 8   # Java 21
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
`kicad-cli pcb drc` reports **0 violations, 0 unconnected** on the routed board
(2-layer, ~152 × 106 mm, ~971 track/via objects). Diodes sit in the inter-row gap
(clear of the switch courtyards); support parts are grouped by net so the routes
stay local. Design rules: 0.25 mm tracks, **0.15 mm clearance** (JLCPCB 6-mil
standard), 0.6/0.3 mm vias. The Gerbers in `gerber/` (zipped as
`workboy_gerbers.zip`) are ready to fab.

## Before ordering — quick sanity
- **J3 USB-C is the real C165948** — Korean Hroparts `TYPE-C-31-M-12`, official KiCad
  footprint `USB_C_Receptacle_HRO_TYPE-C-31-M-12`. Pinout verified (VBUS=A4/A9/B4/B9,
  GND=A1/A12/B1/B12, CC1=A5, CC2=B5, shield=SH); re-DRC = 0 violations. ✅
- Hand-solder J1 (link pigtail) and the 53 switches; J1 is consigned (not in the BOM).
- 2-layer, no controlled impedance needed (8 kHz link); default JLCPCB stackup is fine.
- A human glance over the autorouted traces before a production run never hurts.
