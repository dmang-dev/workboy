# Pre-fabrication checklist

**Can I order a board yet?** Work down this list. Anything marked 🔴 will cost you
a board if you skip it.

> **Status: not yet ordered. Nothing here has been built.** Everything below is
> from design review, not from an assembled unit.

> ### Verification pass 2026-07-28
>
> The three original blockers were investigated against the real KiCad files with
> `kicad-cli` 10.0.5 and `pcbnew`. **Two were false alarms. The third is worse than
> written.** Two new blockers were found that were not on the list at all.
>
> **The bare PCB is electrically sound and could be fabricated today** — DRC is
> genuinely clean (0 violations, 0 unconnected, 886 tracks, 60 vias) and every net
> checked lands where the netlist says. What blocks an order is **mechanical**:
> no mounting holes, and a case built to the wrong size.
>
> Confidence is *not* uniform below — each item says how it was established.

---

## 🔴 Blocking — fix before uploading gerbers

### 1. ~~The board has no mounting holes at all~~ ✅ **RESOLVED 2026-07-28 — four added**

*Was: `grep -c MountingHole` → 0, while `BUILD_PLAN` promised 4× M2.5 and the case
drilled four standoffs. The placeholder's holes at (±61, ±28.5) were fictional.*

Four `MountingHole:MountingHole_2.7mm_M2.5` (**plain NPTH, no copper**) are now
placed, 4.0 mm inset from the `Edge.Cuts` centreline at each corner, symmetric
about the board centre **(150.0, 89.0625)**:

| Ref | Corner | Position (mm) |
|---|---|---|
| **H1** | top-left | **(78.000, 40.000)** |
| **H2** | top-right | **(222.000, 40.000)** |
| **H3** | bottom-left | **(78.000, 138.125)** |
| **H4** | bottom-right | **(222.000, 138.125)** |

**Hole spacing: 144.000 × 98.125 mm** — these are the numbers the case standoffs
must use.

Positions were chosen by scanning clearances against every pad, track, via and part
body. Insets of 4.0–5.5 mm all pass; **6.0 mm fails** because the top-right hole
starts fouling **SW12**. 4.0 mm was taken as it maximises component clearance at
that tightest corner:

| | copper clr | part-body clr | edge clr |
|---|---|---|---|
| H1 | 7.071 mm (SW1) | 6.329 mm | 4.000 mm |
| **H2** | **4.607 mm (SW12)** | **4.475 mm** ← tightest | 4.000 mm |
| H3 | 9.318 mm (R11) | 9.071 mm | 4.000 mm |
| H4 | 24.934 mm (J3) | 22.674 mm | 4.000 mm |

A 5 mm case post needs 2.5 mm of body clearance, so the worst case leaves **1.98 mm
of margin**. Hole edge sits 2.65 mm from the board edge.

**Verified after the change:**
- `kicad-cli pcb drc --severity-all --exit-code-violations` → **0 violations, 0
  unconnected, 0 footprint errors**, exit 0
- Board outline **unchanged** (73.925–226.075 × 35.925–142.200 incl. stroke)
- Drill file carries tool **`T6C2.700` with exactly 4 hits** at those coordinates
- Holes are marked exclude-from-BOM and exclude-from-position-files, so the **CPL
  still lists 131 parts** and `workboy_jlcpcb_bom.csv` is byte-unchanged
- H1–H4 added to `generate_workboy_netlist.py` (135 components, zero net nodes) so
  a future netlist re-import **cannot silently delete them**

> ⚠️ The right-hand edge only has **2.05 mm** of free border (J3 runs close to it) —
> there is no room for a fifth hole mid-span on that side. The corners are the only
> viable positions.

### 2. The real board is **152.000 × 106.125 mm** — the case is sized for 144 × 78 🔴
*Verified directly from `Edge.Cuts` (4 `gr_line` segments): X 74.0–226.0,
Y 36.0–142.124999 → **152.000 × 106.125 mm, 161.31 cm²**. Cross-checked against the
exported profile gerber.*

Three different sizes are in play and **none of the documentation is right**:

| Source | Size | Delta vs real |
|---|---|---|
| **Real board** (`Edge.Cuts`) | **152.000 × 106.125 mm** | — |
| `make_board_step.py` placeholder | 144 × 78 mm | −8.000 × −28.125 |
| `BUILD_PLAN.md` (×3 places) | ~140 × 85 mm | −12.000 × −21.125 |

The case interior is **155.2 × 71.2 mm**, so the real board overruns it by
**34.9 mm** in depth — and is **30 mm deeper than the case's entire outer
envelope**. This is not a tolerance problem; the board is ~40 % deeper than the box.

⚠️ **The placeholder never fit either.** Its 78 mm depth already exceeded the
71.2 mm interior, despite the comment at `make_board_step.py:17` claiming it was
"sized to sit inside the case interior". **Treat the case model as unvalidated, not
merely out of date.**

Fix: drive the case from the board outline instead of from the key field — parse
`Edge.Cuts` so the two cannot drift apart again — then re-check standoff positions
(one currently lands on **SW13**'s through-hole pin) and the square-corner vs
`r=2` interior fillet interference.

> The case script also never re-centres the imported STEP, so the real board lands
> ~150 mm away from the case origin. Export with an explicit origin, or translate
> on import using the board's own bounding box.

### 3. ~~J3 USB-C pad names are unverified~~ ✅ **RESOLVED — false alarm**
*Established with `pcbnew` against the placed footprint, and by diffing the board's
footprint copy against the KiCad 10 library `.kicad_mod`. This item had full
adversarial review; nothing was overturned.*

The old text was wrong on both counts. The netlist never used GCT `USB4085` naming
(`generate_workboy_netlist.py:44` declares
`Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`, which is exactly what is placed
at `workboy.kicad_pcb:4783`), and the shield is called **`SH`** in both — no
KiCad 10 `Connector_USB` footprint uses an `S1` pad at all.

All 10 referenced pad names exist and carry the intended net:

| Net | Pads |
|---|---|
| GND | A1, A12, B1, B12, + 4× SH |
| VBUS | A4, A9, B4, B9 |
| USB_CC1 / USB_CC2 | A5 / B5 |

Sink topology is valid (5.1 kΩ Rd on both CC lines), and D54's SS14 is oriented
correctly — pad 2 (anode) on VBUS, pad 1 (cathode) on +5 V. `A6/A7/A8/B6/B7/B8`
are intentionally netless: this is a power-only connector and the ATmega328P has no
native USB.

> **Still worth 30 seconds before ordering:** that **LCSC C165948** really is the
> HRO TYPE-C-31-M-12 is a vendor-catalogue fact that cannot be checked from these
> files. Compare the LCSC land pattern against the footprint before you buy.

> **Do not add a 16 MHz crystal later without revisiting D54.** The Schottky drops
> ~0.4–0.5 V, so +5 V sits below VBUS. Harmless now (the MCU runs on its internal
> oscillator — there is no crystal in the netlist), but at 16 MHz a 4.75 V source
> minus the drop falls under the 4.5 V minimum.

### 4. ~~Tact switch pad numbering~~ ✅ **RESOLVED** — but the **BOM part is wrong** 🔴
*⚠️ Confidence caveat: the adversarial reviewers for this item all failed to run
(spend limit). The reasoning below is from a single investigation plus the cited
datasheet — **it has not been independently cross-checked.***

The pad-numbering worry was well founded but the wiring is **correct**.
`SW_PUSH_6mm` in KiCad 10.0.5 does use duplicated numbers (four pads: `1,1,2,2`),
and the grouping is right: same-numbered pads sit **6.5 mm apart** on a common Y
(`SW_PUSH_6mm.kicad_mod:290-315`), matching the Omron B3F terminal arrangement
where the tied legs span the long side. The switch closes across the 4.5 mm gap —
so netlist pads 1 and 2 are genuinely **across the contacts**, not shorted.

Every footprint also carries `(duplicate_pad_numbers_are_jumpers no)`, so KiCad
required real copper between each tied pair rather than trusting the leadframe —
and that copper is present. A single bad solder joint per pair will not kill a key.

🔴 **But the ordered part does not match the footprint.** The BOM specifies
**`C720477`** for all 53 switches with comment *"Tactile switch 6x6mm THT"* and
footprint `SW-TH-6.0x6.0` — while the investigation reports C720477 is actually an
**SMD 4×3 mm** tact. I could not confirm that from here (it is a vendor fact), so:

**Open [lcsc.com/product-detail/C720477.html](https://www.lcsc.com/product-detail/C720477.html)
and check the package.** If it is not a 6×6 mm THT part on the B3F 6.5 × 4.5 mm
four-lead pattern, replace it (e.g. Omron B3F-1000/B3F-1002 or equivalent) in
`workboy_jlcpcb_bom.csv` and anywhere else it appears.

> Cheap physical settle: put a DMM across one switch before soldering 53. The legs
> **6.5 mm** apart must beep **unpressed**; the legs **4.5 mm** apart must be open
> until pressed.

---

## 🟡 Decide before ordering

### 4. Which link connector?

> ### ✅ Decision (2026-07-28): land **J1 + J4**. **J5 is parked.**
>
> J1 and J4 both mount on the board face and change nothing about the outline,
> plating or thickness — landing both costs nothing and lets one fab run serve
> either a soldered pigtail or an ordinary link cable.
>
> **J5 (board-edge tongue) was deliberately dropped for rev A.** It costs no
> parts, but it forces an outline change, wants ENIG (**~1.5–2.0×** the
> bare-board line vs HASL) because an inserted edge wears, and — decisively —
> it plugs the board *rigidly into the console with no cable*, which is wrong
> for a keyboard you sit and type on. The analysis is kept in
> `generate_workboy_netlist.py` and below, so revisiting it needs no re-research.

All three land on the **same six nets**; you populate exactly one. Wiring them in
parallel is electrically free.

| | **J1** — 1×6 0.1″ header | **J4** — real EXT socket | **J5** — board-edge tongue |
|---|---|---|---|
| Status | **ready now** | needs footprint drawn | needs footprint **+ outline** |
| Attaches via | soldered cut-cable pigtail | **any standard link cable** | plugs straight into the console |
| Part cost | ~$5–8 (cable to cut) | ~$3–10 (repair part) | **$0 — no part** |
| Board outline | unchanged | unchanged | ⚠️ **changes it** |
| Plating | HASL fine | HASL fine | ⚠️ wants **ENIG** or pads wear |
| Thickness | any | any | ⚠️ socket is ~1.2 mm nominal; **1.6 mm is tight** |
| Ergonomics | permanent tail | best — normal cable | rigid, board hangs off the console |

**J1 + J4 are genuinely free** — both mount on the board face, change nothing about
the outline, plating or thickness. Land both.

**J5 — parked. Notes kept for a possible rev B.**

Not free despite costing no parts:

- **Outline change** — the tongue protrudes, so the case must be re-fitted and the
  board edge redrawn.
- **Finish** — ENIG at **~1.5–2.0×** the bare-board line (HASL is JLCPCB's free
  default). Hard "gold fingers" is **~3.0–5.0×** plus bevelling, and is meant for
  thousands of insertion cycles — overkill for a connector used dozens of times.
  ENIG also *benefits the whole board* given the TQFP-32 and 0402s, so it isn't
  purely a J5 tax. Selective finish (ENIG pads + hard gold fingers) exists if ever
  needed.
- **Thickness is a fit issue, not a cost one** — 1.6 mm is JLCPCB's free default;
  the socket is nominally ~1.2 mm, so 1.6 mm is a tight insert.
- **Ergonomics decided it** — the board plugs rigidly into the console with no
  cable. Fine for a compact direct-attach variant; wrong for a keyboard.

If revisited: put the tongue on a **break-off tab** (mouse-bites / V-score) so one
fab run yields both variants, and order **ENIG — skip hard gold**. The netlist
support is already written and inert behind `EMIT_LINK_EDGE = False`.

**To enable J4:** buy an EXT socket (sources in [`COMPATIBILITY.md`](COMPATIBILITY.md)),
measure it, draw `workboy:GB_EXT_Socket_6P`, set `EMIT_LINK_SOCKET = True`.

**To enable J5:** draw `workboy:GB_EXT_EdgeTongue_6P` (3 pads top + 3 bottom, ~6 mm
tongue) *and* edit the board outline to match, set `EMIT_LINK_EDGE = True`, and
order with ENIG. Bevelling the tongue edge (JLCPCB "gold fingers", extra cost)
makes insertion much kinder.

> ⚠️ **Editing the netlist does not change the board.** After re-running the
> generator you must import the netlist in the KiCad PCB editor, place and route
> the new part, re-run DRC, and re-export gerbers + CPL.

> 🔴 **Correction (2026-07-28): the "land J1 + J4" decision above is NOT
> implemented.** `generate_workboy_netlist.py:55` still has
> `EMIT_LINK_SOCKET = False`, so the J4 block never emits and **J4 has never
> existed in any netlist or board** — the board carries J1 only (3 `J` designators:
> J1, J2, J3).
>
> The old wording here — that the gerbers "were produced *before* J4 existed" —
> had the premise backwards. It implied the exports merely needed refreshing. They
> do not: **the exports are current.** Re-exporting gerbers and drill from the
> present board reproduces `kicad/gerber/*` byte-for-byte across all 26 files,
> except the KiCad version string (10.0.3 → 10.0.5) and the timestamp.
>
> So decide explicitly: either **implement J4** (buy the socket, measure it, draw
> `workboy:GB_EXT_Socket_6P`, flip the flag, re-import, place, route, re-run DRC,
> re-export) — or **amend the decision to say rev A ships J1 only** and defer J4.
> Right now the repo records a decision it has not carried out.

### 5. Board size vs. the cost tier — **worse than written**
The real board is **152.000 × 106.125 mm** (§2), not the ~140 × 85 mm this section
used to assume. That matters for the quote: it exceeds JLCPCB's ≤100 × 100 mm
bracket on **both** axes (X by 52.0 mm, Y by 6.125 mm), and its **161.31 cm²** is
**1.61×** that bracket's 100 cm² ceiling.

So the cheap "5 boards for $7–17" line in `BUILD_PLAN.md:338` **does not apply at
all** — it is a sub-100 mm price. Get a live quote at **152 × 107 mm**, 2-layer,
1.6 mm, 1 oz, HASL, 5 pcs before committing.

If the price is unacceptable, the lever is the **~10 mm key pitch** driving the
outline — nothing electrical needs to change to shrink it.

### 6. Assembly split — outsource the switches or not?
- **SMT only** (recommended in `BUILD_PLAN`): JLCPCB does the MCU, passives, 53
  diodes, LEDs, USB-C. You hand-solder 53 tact switches + the connector.
- **SMT + THT**: adds **$3.50 labour + ~$0.0017/joint + possibly ~$3 unique-part
  fee** ⇒ roughly **$4–7 more** for ~106 joints. Small enough that outsourcing is
  reasonable if you'd rather not do the repetition.

Either way the **link connector is consigned or hand-soldered** — it is excluded
from `workboy_jlcpcb_bom.csv` on purpose.

---

## ✅ Already verified

- **Clean-room ROM** builds (GBDK-2020 → 128 KB MBC1+RAM+BATTERY). No leaked code.
- **Key layout is real**: 53 keys, rows of 12/11/11/11/8, 5u space bar, generated
  from `layout/keymap.py` into both the case and the PCB placement.
- **Pin budget closes exactly** — 18/18 GPIO with zero spare.
- **DRC is genuinely clean** — re-run 2026-07-28 with `kicad-cli pcb drc
  --severity-all` against the current board: **0 violations, 0 unconnected, 0
  footprint errors**, empty exclusions, 886 track segments and 60 vias, so it is
  really routed. *(Caveat: `--schematic-parity` cannot run — there is no schematic,
  the netlist is generated. Board-vs-netlist agreement was checked by comparing
  pads, not by DRC.)*
- **J3 USB-C is correctly wired** — see §3. All pads resolve, sink topology valid.
- **Switch pads 1/2 are across the contacts**, not shorted — see §4.
- **Export artefacts are current, not stale** — gerbers, drill and the zip all
  reproduce byte-identically from the present board.
- **BOM/CPL parity**: CPL lists all 131 designators, BOM lists 130 — J1 is omitted
  deliberately (consigned/hand-soldered). Harmless, but worth a note on the order
  so it does not trigger an engineering query.
- **Electrically correct for every console that runs a GB/GBC cartridge** — all of
  them drive the link at 5 V, so no level shifter. See `COMPATIBILITY.md`.
- **Licence + attribution** in place (`LICENSE`, `NOTICE`).

---

## Order of operations

**Mechanical first — everything that changes copper must happen before the order.**

1. ~~Add mounting holes~~ ✅ **done** (§1) — H1–H4, DRC clean, all artefacts
   re-exported.
2. **Decide J4** (§4 below) — implement it or amend the decision to J1-only. This
   is now the **only remaining thing that would change the gerbers**.
3. **Check `C720477`** on LCSC (§4) and fix the BOM if it is not a 6×6 mm THT tact.
   *(BOM-only — does not affect the board.)*
4. Get a live JLCPCB quote at **152 × 107 mm** (§5).
5. Order 5. Upload `kicad/workboy_gerbers.zip`, `workboy_jlcpcb_bom.csv` and
   `kicad/workboy_cpl_jlcpcb.csv`. Hand-solder switches + connector unless paying
   for THT.
6. **Case is a separate track** — it does not gate the PCB order. Re-derive it from
   the real outline (§2); the standoffs now have real hole positions to hit,
   **144.000 × 98.125 mm** apart.
7. Bring-up: **program the ATmega *before* attaching the link cable** — ISP shares
   the SPI pins. Then follow `BUILD_PLAN` §8.

> If J4 is deferred and `C720477` checks out, **the board is ready to order as it
> stands** — the exported gerbers, drill, CPL and BOM in the repo are current as of
> 2026-07-28 and DRC-clean.

> **Meter the cut cable before connecting.** Reversed SI/SO is listed as a top
> failure mode — the two ends of a link cable are deliberately cross-wired.

---

## Notes on this verification pass

Run 2026-07-28 with `kicad-cli` 10.0.5 and KiCad's bundled `pcbnew`, reading the
board file directly rather than trusting the documentation. What it changed:

| Item | Was | Now |
|---|---|---|
| J3 USB-C pads | blocking | ✅ resolved — premise was factually wrong |
| Switch pad numbering | blocking | ✅ resolved — but exposed a wrong BOM part |
| Case fit | blocking | 🔴 still blocking, and **worse** — and the placeholder never fit either |
| Mounting holes | not on the list | ✅ **fixed same day** — 4 added, DRC clean, artefacts re-exported |
| Board size | ~140 × 85 mm | **152.000 × 106.125 mm**, over the cheap tier on both axes |
| Gerber staleness | assumed stale | ✅ current, byte-identical |
| J1 + J4 decision | recorded as decided | 🔴 never implemented |

**Not independently cross-checked** (their reviewers failed to run): the switch
tie-topology reasoning and the C720477 package claim in §4. Both are flagged inline.

**Cannot be settled from these files at all** — vendor-catalogue facts needing a
datasheet: the identity of **C165948** and the package of **C720477**.
