# WorkBoy case (parametric, OpenSCAD)

A starter two-piece clamshell — top plate with key cutouts + bottom tray with
PCB standoffs, heat-set screw bosses, and a rear cable slot. Defaults to
~150 × 85 mm to match the original WorkBoy footprint.

## Render / export
Install [OpenSCAD](https://openscad.org/), open `workboy_case.scad`, set `part`
and press **F6**, or from the command line:
```sh
openscad -D 'part="top"'    -o workboy_top.stl    workboy_case.scad
openscad -D 'part="bottom"' -o workboy_bottom.stl workboy_case.scad
```

## Key parameters (top of the file)
| Param | Meaning |
|---|---|
| `pitch` | key center-to-center spacing (mm) |
| `cols`, `rows` | key grid (placeholder 10×5 = 50; target 53) |
| `keycap`, `cap_clear` | keycap size + plate-hole clearance |
| `case_h`, `wall`, `plate_th`, `floor_th` | shell dimensions |
| `standoff_h` | PCB rest height (clears THT lead tails) |
| `insert_d` | heat-set insert pocket dia — **verify against your inserts** |

## This is a starting point — refine before printing
1. **Real layout:** the grid is uniform. Replace it with the actual staggered
   QWERTY + 9 app keys + arrows + space/enter (53 keys). Easiest: export the
   switch positions / board outline from KiCad (STEP or DXF) and align the plate
   holes to them so caps sit over real switches.
2. **Keycap interface:** holes are sized for floating caps captured by the plate.
   Tune `cap_clear` with a one-row fit-test print before committing 53 holes.
3. **Material:** PETG for the shell (survives heat-set inserts and a warm
   console); resin for crisp legended keycaps.
4. **Fasteners:** M2.5 brass heat-set inserts in the bosses, screws from the top.
   For hidden screws, flip to inserts-in-plate / screws-from-bottom (Scheme B in
   BUILD_PLAN §5).
5. **Cable:** the rear slot is for a soldered link pigtail; add a printed strain
   relief or grommet.

## build123d port (Python, imports the KiCad board STEP)
[`workboy_case_b123d.py`](workboy_case_b123d.py) is a build123d port of this model.
It exports `workboy_top.stl`, `workboy_bottom.stl`, and a combined
`workboy_case_assembly.step`, and — if `kicad/workboy_board.step` exists — imports
the board and places it on the standoffs for a fit check.

```sh
pip install build123d
python ../kicad/make_board_step.py     # placeholder board STEP (replace with KiCad export)
python workboy_case_b123d.py
```
Once you run the KiCad layout, export the real board (`File ▸ Export ▸ STEP`) over
`kicad/workboy_board.step` and re-run — the case aligns to the actual switch/mount
positions.
