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

### 2. ~~The case is sized for 144 × 78~~ ✅ **RESOLVED 2026-07-28 — case rebuilt from the board**

*Was: three different board sizes in the docs and none of them right. The case
interior was **155.2 × 71.2 mm** for a **152.000 × 106.125 mm** board — it overran
by 34.9 mm in depth and was 30 mm deeper than the case's whole outer envelope. The
placeholder never fitted either, so the model was unvalidated, not merely stale.*

`case/workboy_case_b123d.py` was rewritten to **parse `kicad/workboy.kicad_pcb` at
build time**. The outline, the four mounting-hole positions, the key pitch and the
key-field offset are all read from the board — nothing is hard-coded, so the case
cannot drift from the PCB again. It **refuses to export** if the board does not fit.

| | Old | New |
|---|---|---|
| Outer | 160 × 76 × 22 mm | **160.000 × 114.125 × 22.000 mm** |
| Interior | 155.2 × 71.2 mm | **155.200 × 109.325 mm** |
| vs board 152.000 × 106.125 | ✗ 34.9 mm short | ✅ **1.600 mm clearance per side** |
| Standoffs | (±61, ±28.5) — matched no real hole | **(±72.000, ±49.0625)** = H1–H4 |
| Sized from | key field | **the board outline** |

**Verified independently** (re-derived from the board and the exported solids, not
from the script's own claims):

- **Key cutout alignment: worst mismatch 0.000000 mm across all 53 keys.** Every
  cutout is centred on its switch.
- Board centring error **0.0000 mm** in both axes.
- **4.095 mm** of air under the protruding through-hole leads (they reach 1.905 mm
  below the PCB — the old model never accounted for them).
- **1.865 mm** headroom between the tallest part (18.135 mm) and the top plate.
- `tests/run_ci.py` → `case-export PASS`.

Two things the rewrite had to fix beyond size:

- **The key field is not centred on the board.** There is a ~48 mm electronics strip
  below the last key row, so the field sits **+19.0625 mm** from the board centre.
  `keymap.centers()` is origin-centred on the *key field*, the case on the *board*.
  The offset is now derived from the real switch coordinates.
- **Screw bosses and PCB standoffs had to merge.** With 1.6 mm of clearance there is
  no room for separate corner bosses beside a board that fills the interior — they
  would collide with it. One M2.5 screw per corner now passes through the top plate,
  through the PCB hole, into an insert in the boss, so the same fastener closes the
  case and retains the board. The clearance scan behind §1 already proved a 7 mm
  boss fits at all four holes.

> 🔴 **`kicad/make_board_step.py` has been deleted, and this mattered.** It wrote a
> placeholder rectangle to `kicad/workboy_board.step` — **and `tests/run_ci.py` ran
> it on every CI run**, silently overwriting the real exported board with a 144 × 78
> rectangle. Regenerate the real one with:
> ```sh
> kicad-cli pcb export step --output kicad/workboy_board.step kicad/workboy.kicad_pcb
> ```

> ⚠️ **Remaining case work is connector access, not fit** — see §7.

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

✅ **BOM part corrected 2026-07-28 — `C720477` was indeed the wrong part.**

Checked on LCSC: **`C720477` is XUNPU `TS-1088-AR02016`, package "SMD,4x3mm",
surface mount, 2 terminals.** Wrong size, wrong mount type, wrong terminal count —
all 53 switches were specified as a part that cannot be fitted to this footprint.

Replaced with **`C42416249` — SHOU HAN `SH-6X6X8H-CJ`**:

| | |
|---|---|
| Package | **`DIP-4P,6x6mm`** — through-hole, 4 legs |
| **Lead spacing** | **6.5 × 4.5 mm** — matches `SW_PUSH_6mm` exactly |
| Body / height | 6 × 6 mm, 8 mm actuator |
| Life | 100,000 cycles · SPST · 50 mA · 12 V |
| Stock / price | 8,480 · ~$0.0124 ea @ 20+ (≈ **$1.30 for 100**) |

8 mm was chosen because the case already models the switch ~8.5 mm above the PCB.
**The whole SH-6X6X\*H-CJ family shares the identical 6.5 × 4.5 mm footprint** at
4.3 / 5.5 / 6.5 / 8 / 9 mm, so the actuator height can be re-picked when the keycaps
are designed **without touching the board** — only the BOM line changes.

> The `Footprint` column was also wrong (`SW-TH-6.0x6.0`, a name matching nothing);
> it now carries LCSC's own `DIP-4P,6x6mm` string.

#### 🔴 And a second wrong part number: J2

Found while costing the BOM. **`C2718` is an onsemi `FDA50N50` — a 500 V, 48 A
N-channel MOSFET**, not a 2×3 pin header. Confirmed on the LCSC product page
(category *Discrete Semiconductors → Transistors → FETs, MOSFETs*).

Replaced with **`C42431837` — JXTCONN `PH2.54-2X3P-H25`**: category *Headers, Male
Pins*, 2×3 six-pin dual row, 2.54 mm pitch, through-hole, gold-plated, 3 A / 1 kV,
39,180 in stock, **$0.0293 ea @ 20+**.

> **Two of the fourteen BOM lines pointed at parts that could not be fitted.** Both
> were plausible-looking C-codes that nobody had opened. If any other line matters
> to you, open its LCSC page before ordering — the footprints are verified against
> the real land patterns, but a part *number* is only as good as the last person who
> checked it.

### 4b. 🔍 Full BOM audit — **every line opened on LCSC (2026-07-28)**

Prompted by two bad part numbers in a row. All 14 lines checked for *identity,
value, package and availability* — not just existence.

| Line | LCSC | What it actually is | Verdict |
|---|---|---|---|
| U1 ATmega328P-AU | `C14877` | Microchip ATMEGA328P-AU · 5,662 stock · $2.14 | ✅ |
| C1–C4 100nF 0402 | `C1525` | Samsung CL05B104KO5NNNC · 100nF **0402** 16 V X7R · 1.39 M | ✅ |
| C5,C6 10µF 0805 | `C15850` | Samsung CL21A106KAYNNNE · 10µF **0805** 25 V X5R · 295 k | ✅ |
| D1–D53 1N4148W | `C2099` | JSCJ 1N4148W **SOD-123** · 32,050 · $0.0124 | ✅ |
| D54 SS14 | `C2480` | MDD SS14 **SMA** · $0.019 (MOQ 50) | ✅ |
| J3 USB-C | `C165948` | **Korean Hroparts TYPE-C-31-M-12** · 246,285 · $0.17 | ✅ *(also settles §3)* |
| SW1–53 tact | `C42416249` | SHOU HAN SH-6X6X8H-CJ · DIP-4P 6×6 · 8,480 | ✅ *(fixed, §4)* |
| J2 ISP header | `C42431837` | JXTCONN PH2.54-2X3P-H25 · 2×3 male THT · 39,180 | ✅ *(fixed, §4)* |
| R1–R3 10k 0402 | ~~`C25744`~~ → **`C60490`** | was UNI-ROYAL 0402WGF1002TCE — right part, **out of stock** | ✅ **replaced** |
| R4–R6 220R 0402 | ~~`C25091`~~ → **`C112291`** | was UNI-ROYAL 0402WGF2200TCE — right part, **out of stock** | ✅ **replaced** |
| R7–R9 1k 0402 | ~~`C11702`~~ → **`C106235`** | was UNI-ROYAL 0402WGF1001TCE — right part, **out of stock** | ✅ **replaced** |
| R10,R11 5.1k 0402 | ~~`C25905`~~ → **`C105872`** | was UNI-ROYAL 0402WGF5101TCE — right part, **out of stock** | ✅ **replaced** |
| LED1 red "0805" | ~~`C2286`~~ → **`C2295`** | was KENTO **KT-0603R — 0603**, not 0805 | 🔴 **wrong package — fixed** |
| LED2,3 green "0805" | ~~`C72043`~~ → **`C2297`** | was EVERLIGHT 19-217 — **0603** *and* unavailable | 🔴 **wrong package — fixed** |

#### 🔴 Both LEDs were the wrong package

`C2286` and `C72043` are **0603** parts, but the board has **0805** land patterns
(`LED_SMD:LED_0805_2012Metric`). A 0603 body hand-solders onto 0805 pads, but in
reflow it risks tombstoning and misplacement — pick-and-place positions to the
part's own body, not the pad.

Replaced with the same manufacturer's genuine 0805 parts, both well stocked:
**`C2295` KT-0805R** (red, 101,200) and **`C2297` KT-0805G** (green, 1,996,800).

#### ⚖️ The 0402 resistors depend on **who assembles the board**

The two catalogues disagree, and the right part number is different for each path:

| | LCSC retail (hand-buy) | JLCPCB library (PCBA) |
|---|---|---|
| **UNI-ROYAL `0402WGF*TCE`** | ❌ out of stock | ✅ **Basic**, stocked (1.1–2.1 M) |
| **YAGEO `RC0402FR-07*`** | ✅ in stock (0.2–1.4 M) | ⚠️ **Extended** (per-part fee) |

Electrically identical — **0402, ±1 %, 62.5 mW, 50 V, ±100 ppm/℃, thick film** — so
this is purely a sourcing choice.

**`workboy_jlcpcb_bom.csv` carries the UNI-ROYAL parts**, because it is the JLCPCB
*assembly* BOM and `BUILD_PLAN` outsources SMT. JLCPCB sources from its own library,
where these are Basic and in stock, so LCSC's retail shortage is irrelevant and you
avoid four Extended-part fees.

| Ref | Value | PCBA (in the BOM) | Hand-build alternative |
|---|---|---|---|
| R1–R3 | 10 kΩ | **`C25744`** 0402WGF1002TCE | `C60490` RC0402FR-0710KL |
| R4–R6 | 220 Ω | **`C25091`** 0402WGF2200TCE | `C112291` RC0402FR-07220RL |
| R7–R9 | 1 kΩ | **`C11702`** 0402WGF1001TCE | `C106235` RC0402FR-071KL |
| R10,R11 | 5.1 kΩ | **`C25905`** 0402WGF5101TCE | `C105872` RC0402FR-075K1L |

> **If you hand-assemble, swap in the right-hand column** — LCSC cannot sell you the
> left-hand parts today. MOQ there is 100 in multiples of 100, ~$0.55 per value.

> 🪤 **The stock trap:** every LCSC product page has `... | In Stock | LCSC
> Electronics` in its `<title>` as **static SEO boilerplate — even for
> out-of-stock parts**. It fooled this review once. Read stock from the page body,
> where an unavailable part shows "Out of Stock" and a "Notify Me" button instead of
> "Add to Cart".

> **Tally: 8 of 14 lines were wrong.** Four named a part that could not be fitted
> (2 outright wrong parts, 2 wrong package) and four named parts that could not be
> bought. All eight are now corrected and individually verified. The footprints had
> been checked against real land patterns all along — it was the *part numbers* that
> nobody had ever opened.
>
> **Every line is now confirmed against its own LCSC page**, with stock read from
> the page body. No board change came out of any of it: the `.kicad_pcb` carries no
> LCSC part numbers, so the gerbers, drill and CPL were never affected.

### 4c. JLCPCB **Basic vs Extended** — every SMT part checked (2026-07-28)

Extended parts carry a per-unique-part loading fee, so this drives assembly cost
more than the components do. Checked directly in JLCPCB's parts library:

| Part | LCSC | Class | JLC stock | @1+ |
|---|---|---|---|---|
| 100nF 0402 | `C1525` | ✅ **Basic** | 46,782,818 | $0.0053 |
| 10 µF 0805 | `C15850` | ✅ **Basic** | 10,801,486 | $0.1191 |
| SS14 | `C2480` | ✅ **Basic** | 2,084,080 | $0.0189 |
| Green LED 0805 | `C2297` | ✅ **Basic** | 2,977,165 | $0.0162 |
| 10 kΩ 0402 | `C25744` | ✅ **Basic** | — | — |
| 220 Ω 0402 | `C25091` | ✅ **Basic** | — | — |
| 1 kΩ 0402 | `C11702` | ✅ **Basic** | 1,120,826 | — |
| 5.1 kΩ 0402 | `C25905` | ✅ **Basic** | 2,109,090 | — |
| **ATmega328P-AU** | `C14877` | ⚠️ Extended | 29,242 | $2.4159 |
| **1N4148W** ×53 | `C2099` | ⚠️ Extended | 61,717 | $0.0123 |
| **USB-C** | `C165948` | ⚠️ Extended | 264,067 | $0.1843 |
| **Red LED 0805** | `C2295` | ⚠️ Extended | 102,716 | $0.0115 |

**8 Basic, 4 Extended.** Keeping the UNI-ROYAL resistors (§4) rather than the YAGEO
ones cut Extended from 8 to 4 — worth roughly $12 in loading fees, i.e. more than
the bare PCBs cost.

The four that remain are hard to avoid: the MCU, the USB-C receptacle and the
switching diode have no Basic equivalent for this design. Only the **red LED** is
casually swappable — its green sibling `C2297` *is* Basic, so if you want one fewer
Extended line, use a Basic red 0805 or make the power LED green too.

> 🪤 **JLCPCB's page title lies the same way LCSC's does.** Every search renders
> `No Results Found for <code>` into `<title>` **before** the client-side fetch
> returns, then the body fills in with the real hit. Judging by the title reports a
> part as missing when it is right there. This produced a wrong conclusion earlier in
> this very review — the UNI-ROYAL resistors were reported absent from JLCPCB's
> library when they are in fact **Basic and stocked**. Read the body, not the title.

> Cheap physical settle: put a DMM across one switch before soldering 53. The legs
> **6.5 mm** apart must beep **unpressed**; the legs **4.5 mm** apart must be open
> until pressed.

---

## 🟡 Decide before ordering

### 4. Which link connector?

> ### ✅ **FINAL for rev A (2026-07-28): ship J1 only. J4 and J5 are both deferred.**
>
> **This is what the board already is** — `EMIT_LINK_SOCKET` and `EMIT_LINK_EDGE`
> are both `False`, so J4 and J5 have never appeared in any netlist or board. The
> exported gerbers, drill, CPL and BOM in this repo are **correct as they stand and
> need no re-export** for this decision.
>
> **Why J1 only.** J4 is not free in the way it first looked. It costs nothing in
> *board area*, but it does cost a **footprint that does not exist and cannot be
> drawn without the physical part in hand** — you must buy an EXT socket, measure
> it, draw `workboy:GB_EXT_Socket_6P`, re-import, place, route, re-run DRC and
> re-export. That is the entire remaining critical path for rev A, in service of a
> connector whose only benefit over J1 is cable convenience. A soldered pigtail
> works on day one.
>
> **Rev A proves the design; rev B can add the socket** once a real board has shown
> the protocol works end to end — and by then the socket can be measured against a
> board that exists.
>
> **J5 (board-edge tongue) stays parked** for the reasons below: it forces an
> outline change, wants ENIG (**~1.5–2.0×** the bare-board line vs HASL) because an
> inserted edge wears, and — decisively — it plugs the board *rigidly into the
> console with no cable*, which is wrong for a keyboard you sit and type on.
>
> The full analysis for both is kept here and in `generate_workboy_netlist.py`, and
> the netlist support is already written and inert, so revisiting either needs no
> re-research.

**What this means practically:** populate **J1**, a 1×6 0.1″ header, and attach a
cut link cable as a pigtail. Meter it first — see the warning at the end of this
file, reversed SI/SO is a top failure mode.

All three options land on the **same six nets**; you populate exactly one. Wiring
them in parallel would be electrically free — the cost is footprint work, not area.

| | **J1** — 1×6 0.1″ header ✅ **rev A** | **J4** — real EXT socket ⏸ rev B | **J5** — board-edge tongue ⏸ parked |
|---|---|---|---|
| Status | **shipping — on the board now** | needs footprint drawn | needs footprint **+ outline** |
| Attaches via | soldered cut-cable pigtail | **any standard link cable** | plugs straight into the console |
| Part cost | ~$5–8 (cable to cut) | ~$3–10 (repair part) | **$0 — no part** |
| Board outline | unchanged | unchanged | ⚠️ **changes it** |
| Plating | HASL fine | HASL fine | ⚠️ wants **ENIG** or pads wear |
| Thickness | any | any | ⚠️ socket is ~1.2 mm nominal; **1.6 mm is tight** |
| Ergonomics | permanent tail | best — normal cable | rigid, board hangs off the console |

**J4 — deferred to rev B. Notes kept.** It changes nothing about the outline,
plating or thickness, so it can be added later at no cost to the board. What it
needs is a **footprint drawn from a physical socket**, which is why it is not in
rev A.

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

> ✅ **Resolved 2026-07-28 — rev A ships J1 only** (see the decision box above).
> The repo previously recorded a "land J1 + J4" decision it had never carried out;
> the record now matches the board.
>
> For the record, so the old wording is not resurrected: the note that the gerbers
> "were produced *before* J4 existed" had its premise backwards. It implied the
> exports needed refreshing. They did not — **J4 never existed at all**, and the
> exports were already current. The board carries three `J` designators: J1, J2, J3.

### 5. ~~Board size vs. the cost tier~~ ✅ **QUOTED 2026-07-28 — ordering 10**

> ### 📦 **Decision: order 10 boards, not 5.**
> $86.50 all-in, **$8.65/board** — 28 % cheaper per board than ordering 5, for
> $26.75 more total. The five extra boards cost ~$5.35 each.

Live JLCPCB instant quote at **152 × 107 mm**, 2-layer, FR-4 TG135, 1.6 mm,
HASL (with lead), 1 oz, green, flying-probe tested:

| Line item | 5 pcs | **10 pcs (chosen)** |
|---|---|---|
| Engineering fee | $4.00 | **$4.00** |
| Board | $7.80 | **$15.60** |
| Build time (2 days) | $0.00 | **$0.00** |
| **PCB subtotal** | $11.80 | **$19.60** |
| Shipping — DHL Express (DDP), 2–4 days | $27.92 | **$28.06** |
| Components (LCSC, with volume breaks) | $20.03 | **$38.84** |
| **Total** | $59.75 | **$86.50** |
| **Per board** | $11.95 | **$8.65** |

**Why 10 is the sweet spot.** The fixed costs barely move: the engineering fee is
flat $4.00 and shipping rose **14 ¢** going from 5 to 10 boards. Board cost is
linear at ~$1.56 each. So at qty 5 you pay $7.94/board for PCB + shipping of which
**$7.18 is fixed overhead** — at 10 that halves.

| Qty | PCB + shipping | Parts | Total | Per board |
|---|---|---|---|---|
| 5 | $39.72 | $20.03 | $59.75 | $11.95 |
| **10** | **$47.66** | **$38.84** | **$86.50** | **$8.65** |
| 20 | $64.58 | $77.69 | $142.27 | $7.11 |
| 30 | $81.58 | $116.53 | $198.11 | $6.60 |

**The knee is at 10.** 5→10 saves $3.30/board; 10→20 only another $1.54, and 20→30
just $0.51 — past 10 the fixed costs are amortised and you are mostly buying parts
at near-flat prices.

Qty 10 also **removes the MOQ waste**: you need 530 diodes and 530 switches, so the
100-piece minimums that were mostly scrap at qty 5 get used, and the diodes cross
the 300+ price break ($0.0124 → $0.0101).

**The size penalty is only $7.80.** The board does leave JLCPCB's ≤100 × 100 mm
bracket on both axes, but that is the entire cost of it — the identical 5-pc order
at 100 × 100 mm quotes **$4.00** (board free, engineering fee only). Going to 1.61×
the area is not a tier jump worth redesigning around.

> 💡 **Shipping is the real cost — $27.92, over twice the PCBs.** That figure is
> DHL Express (DDP) and is only an estimate; slower/cheaper methods normally exist
> and the number depends on destination. The quote page was also showing "Save
> $30.00 / Save $20.00" coupons. **If cost matters, attack shipping, not board
> area.**

#### ⚠️ The PCB quote is the **bare board only** — no parts, no assembly

Components are a separate LCSC order. Every price below was read off the vendor
page during the 2026-07-28 audit:

| Item | LCSC | Qty/board | Unit | Per board |
|---|---|---|---|---|
| **ATmega328P-AU** | C14877 | 1 | $2.14 | **$2.14** |
| 1N4148W diode | C2099 | 53 | $0.0101 @300+ | $0.54 |
| Tact switch | C42416249 | 53 | $0.0124 | $0.66 |
| 10 µF 0805 | C15850 | 2 | $0.1004 | $0.20 |
| USB-C receptacle | C165948 | 1 | $0.1349 @100+ | $0.13 |
| LEDs ×3 | C2295 / C2297 | 3 | ~$0.012 | $0.04 |
| SS14 Schottky | C2480 | 1 | $0.019 | $0.02 |
| ISP header | C42431837 | 1 | $0.025 @200+ | $0.03 |
| 11 resistors + 4× 100nF | — | 15 | ~$0.005 | $0.08 |
| | | | **≈ $3.88/board at qty 10** | |

**The MCU alone is 55 % of the parts cost.** Everything else together is under
$1.75, because the two 53× lines are cheap in bulk.

> **SMT assembly is not included in any of the above.** If you want JLCPCB to place
> the MCU, passives, diodes, LEDs and USB-C rather than hand-soldering 0402s and a
> TQFP-32, that is their PCBA service, quoted separately — see §6. The 53 switches
> and J1 are hand-soldered either way. Note the ~$12 of Extended-part loading fees
> (§4c) is a **per-order** cost, so it also halves per board at qty 10.

> **Shipping is the single largest line at $28.06** — more than the PCBs. It barely
> moves with quantity, which is exactly why 10 beats 5. LCSC ships separately again;
> both vendors share a parent but not a parcel.

If you ever *do* want to shrink it, the lever is the key pitch driving the outline —
nothing electrical changes. The real pitch is **12.0 mm**, measured from the switch
coordinates, *not* the "~10 mm" quoted in `BUILD_PLAN`; the 53 switches sit on an
exact 12.0 mm grid spanning 132 × 48 mm.

> Quoted from dimensions, not from an upload. Once the real gerbers are parsed the
> figure can move slightly — but the board is well inside standard capabilities
> (2-layer, 0.25 mm track, 0.15 mm clearance, 0.3 mm drill), so no special-case
> surcharge is expected.

### 6. Assembly split — outsource the switches or not?
- **SMT only** (recommended in `BUILD_PLAN`): JLCPCB does the MCU, passives, 53
  diodes, LEDs, USB-C. You hand-solder 53 tact switches + the connector.
- **SMT + THT**: adds **$3.50 labour + ~$0.0017/joint + possibly ~$3 unique-part
  fee** ⇒ roughly **$4–7 more** for ~106 joints. Small enough that outsourcing is
  reasonable if you'd rather not do the repetition.

Either way the **link connector is consigned or hand-soldered** — it is excluded
from `workboy_jlcpcb_bom.csv` on purpose.

### 7. ~~The connectors sit inland~~ ✅ **RESOLVED 2026-07-28 — J3 moved to the right edge**

*Was: J3 sat **16.07 mm inside** the outline, so no USB-C plug could reach it —
you would have needed a 16 mm channel through the case wall.*

J3 is now **flush with the right edge**, rotated 90° so the mating face points
outward, body front on the outline and the courtyard overhanging by 0.525 mm (normal
for an edge-mounted connector). It is a real plug-through port.

| | Before | After |
|---|---|---|
| J3 → right edge | 16.07 mm inland | **−0.525 mm (overhangs)** |
| R11 (CC2 pulldown) → J3 | 138.31 mm | **9.37 mm** |
| D54 (VBUS Schottky) → J3 | 131.51 mm | **12.35 mm** |
| Total VBUS copper | ~112 mm across the board | **13.7 mm** |

The support cluster moved with it, which fixed a second latent problem. `gen_pcb.py`
placed support parts with a **row-wrapping flow**, and the `["J3","R10","R11","D54"]`
group happened to straddle a wrap — stranding the CC2 pulldown and the VBUS diode on
the far side of the PCB and dragging the unfused power input across the whole board.
That was an artifact of the layout algorithm, not a decision. The cluster is now
placed explicitly.

**J1 and J2 were never a problem** and are unchanged: J1 (9.47 mm in) is a soldered
pigtail — a wire exit, not a plug — and J2 is a programming header used once with the
lid off.

**Verified after the move:** DRC **0 violations, 0 unconnected, 0 footprint errors**;
board outline unchanged at 152.000 × 106.125 mm; 135 footprints, 1011 track/via
objects; drill still carries 4× `T6C2.700`; CPL still 131 parts. Case regenerates
identically and now cuts its **J3 port and J1 slot from the real connector
coordinates** rather than hard-coded ones.

> The board outline is now **pinned** in `gen_pcb.py` (`BX0..BY1`) instead of being
> derived from the bounding box of whatever happens to be placed. Deriving it meant
> moving any single part could silently resize the board — and the size is
> load-bearing for the case, the mounting holes and the quote. The placement is
> asserted to fit inside it instead, and the script refuses to write a board that
> overflows.

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
2. ~~Decide J4~~ ✅ **done** (§4) — **rev A ships J1 only.** Nothing further to
   change on the board; the exported artefacts already reflect this.
3. ~~Check `C720477`~~ ✅ **done** (§4) — it was an SMD 4×3 mm part; the BOM now
   specifies **`C42416249`**, a real 6×6 mm THT tact on the matching footprint.
4. ~~Get a live JLCPCB quote~~ ✅ **done** (§5) — **$19.60 for 10 boards** plus
   $28.06 shipping. **10 chosen over 5**: 28 % cheaper per board for $26.75 more.
5. **Order 10** (§5). Upload `kicad/workboy_gerbers.zip`, `workboy_jlcpcb_bom.csv`
   and `kicad/workboy_cpl_jlcpcb.csv`. Hand-solder switches + connector unless
   paying for THT. Buy components separately from LCSC — one 100-piece lot of each
   resistor value covers the run.
6. ~~Case~~ ✅ **rebuilt from the board** (§2) — fits with 1.6 mm per side, all 53
   cutouts aligned. Remaining case decision is **connector access** (§7), not fit.
7. Bring-up: **program the ATmega *before* attaching the link cable** — ISP shares
   the SPI pins. Then follow `BUILD_PLAN` §8.

> ### 🟢 **Ready to order — board and BOM both.**
> Every blocker is closed: mounting holes added, J3 moved to the edge, J4 deferred
> to rev B, and **all 14 BOM lines individually verified against LCSC** (§4b) —
> eight of them had to be corrected. The gerbers, drill, CPL, BOM and STEP are
> current as of 2026-07-28 and DRC-clean (**0 violations, 0 unconnected, 0 footprint
> errors**), and every part is a real, in-stock, correctly-packaged component.
>
> Upload `kicad/workboy_gerbers.zip`, `workboy_jlcpcb_bom.csv` and
> `kicad/workboy_cpl_jlcpcb.csv`.
>
> **Basic/Extended is settled too** (§4c): **8 Basic, 4 Extended** — MCU, USB-C,
> 1N4148W and the red LED. The BOM deliberately carries the JLCPCB-Basic resistors,
> which saved four Extended-part fees (~$12, more than the PCBs cost).
>
> ⚠️ **If you hand-assemble instead**, swap the four resistors to the YAGEO codes in
> §4 — LCSC cannot sell you the Basic ones today.
>
> **Cost (§5) — ordering 10: PCBs $19.60 + components $38.84 + shipping $28.06 =
> $86.50, or $8.65 per board** self-assembled. That is 28 % cheaper per board than
> ordering 5, for $26.75 more total, because the $4.00 engineering fee and ~$28
> shipping do not scale. The bare-PCB quote alone is $19.60 — it does **not** include
> parts or assembly. Upload `kicad/workboy_gerbers.zip`, `workboy_jlcpcb_bom.csv`
> and `kicad/workboy_cpl_jlcpcb.csv`.
>
> The case is rebuilt from the board file and fits, so it gates nothing either.
>
> Two vendor facts still rest on LCSC's catalogue rather than a datasheet you have
> read: that **C165948** really is the HRO `TYPE-C-31-M-12` (§3), and the exact
> actuator feel of **C42416249** (§4). Neither can break the board — the footprints
> are verified against the real land patterns — but glance at both before buying.

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
| Case fit | blocking | ✅ **fixed** — case rebuilt from the board file; 53/53 cutouts align to 0.000000 mm |
| Mounting holes | not on the list | ✅ **fixed same day** — 4 added, DRC clean, artefacts re-exported |
| Board size | ~140 × 85 mm | **152.000 × 106.125 mm**, over the cheap tier on both axes |
| Gerber staleness | assumed stale | ✅ current, byte-identical |
| J1 + J4 decision | recorded as decided | ✅ **amended — rev A ships J1 only**, matching what the board always was |

**Since confirmed on LCSC:** the `C720477` claim was correct — it is XUNPU
`TS-1088-AR02016`, "SMD,4x3mm", 2 terminals. The BOM now specifies **`C42416249`**
(SHOU HAN `SH-6X6X8H-CJ`), whose 6.5 × 4.5 mm lead pattern matches `SW_PUSH_6mm`.

**Still resting on the vendor catalogue rather than a datasheet you have read:**
that **C165948** is the HRO `TYPE-C-31-M-12`. The footprint is verified against the
real KiCad land pattern either way, so this cannot break the board — but it is worth
a glance before buying.
