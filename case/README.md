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

## The key field is generated — do not hand-edit it

Plate cutouts come from **`layout/keymap.py`**, the single source of truth, via
`layout/gen_layout.py` → **`case/key_positions.scad`**. `workboy_case.scad`
`include`s that file and cuts one rectangle per key at its real centre, scaling
each by its own width in key units. The build123d port imports the same data
directly (`from keymap import centers`).

So both case models already carry the **real 53-key layout**: rows of
**12 / 11 / 11 / 11 / 8**, 52 keys at 1u plus the **5u space bar**, on a
12 × 5 unit field at 12 mm pitch (144 × 60 mm).

**After changing `keymap.py`, re-run the generator** or the case silently drifts
from the PCB:
```sh
python layout/gen_layout.py    # rewrites key_positions.scad, scancode_map.h, keymap.svg, key_positions.json
python tests/run_ci.py
```

## Key parameters (top of the file)
| Param | Meaning |
|---|---|
| `pitch` | key center-to-center spacing (mm) — **must match `PITCH` in `gen_layout.py`** |
| `key_gap` | plate cutout = key cell minus this (cap clearance) |
| `key_pos[]` | **generated** — `[cx, cy, width_units]` per key, origin = case centre |
| `case_h`, `wall`, `plate_th`, `floor_th` | shell dimensions |
| `standoff_h` | PCB rest height (clears THT lead tails) |
| `insert_d` | heat-set insert pocket dia — **verify against your inserts** |

## This is a starting point — refine before printing
1. **Keycap interface:** holes are sized for floating caps captured by the plate.
   Tune `cap_clear` with a one-row fit-test print before committing 53 holes.
3. **Material:** PETG for the shell (survives heat-set inserts and a warm
   console); resin for crisp legended keycaps.
4. **Fasteners:** M2.5 brass heat-set inserts in the bosses, screws from the top.
   For hidden screws, flip to inserts-in-plate / screws-from-bottom (Scheme B in
   BUILD_PLAN §5).
5. **Cable:** the rear slot is for a soldered link pigtail; add a printed strain
   relief or grommet.

## build123d model — **the board file is the single source of truth**

[`workboy_case_b123d.py`](workboy_case_b123d.py) is the maintained model. It exports
`workboy_top.stl`, `workboy_bottom.stl` and a combined `workboy_case_assembly.step`.

**Every dimension is parsed from `kicad/workboy.kicad_pcb` at build time** — the
outline, the four mounting-hole positions, the key pitch and the key-field offset.
Nothing is hard-coded, so the case cannot drift from the PCB. Change the board,
re-run this, done.

```sh
python -m venv .venv && .venv/bin/pip install build123d   # never install system-wide
python workboy_case_b123d.py
```

It refuses to export if the board does not fit, and reports the numbers it used:

```
board  : 152.000 x 106.125 mm, centre (150.0000, 89.0625) [from workboy.kicad_pcb]
case   : 160.000 x 114.125 x 22.000 mm outer
         155.200 x 109.325 mm interior (1.6 mm clearance per side)
key    : pitch 12.0 mm measured from the board; field offset (+0.0000, +19.0625)
mounts : 4 at (-72.000,-49.063), (-72.000,+49.062), (+72.000,-49.063), (+72.000,+49.062)
```

For the visual assembly it also imports `kicad/workboy_board.step` if present, and
checks that the board centres, that the through-hole leads clear the floor and that
the tallest part clears the top plate. Generate that STEP with:

```sh
kicad-cli pcb export step --output kicad/workboy_board.step kicad/workboy.kicad_pcb
```

> ⚠️ There used to be a `kicad/make_board_step.py` that produced a **placeholder
> rectangle** into that same path — and CI ran it, so it silently overwrote the real
> export. It has been removed. If you find it referenced anywhere, that reference is
> stale; use the `kicad-cli` line above.

> **The key field is not centred on the board.** The PCB carries a ~48 mm
> electronics strip below the last key row, so the key field sits **+19.0625 mm**
> from the board centre. `keymap.centers()` is origin-centred on the *key field*;
> the case is centred on the *board*. The script derives that offset from the real
> switch coordinates rather than assuming it.
