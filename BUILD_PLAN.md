# Game Boy WorkBoy — Recreation Build Plan

A buildable, modern recreation of Nintendo's unreleased **WorkBoy** keyboard
accessory (Source R&D / Fabtek / Montague-Weston, 1992): a QWERTY keyboard that
plugs into the Game Boy Link Port and turns the console into a PDA, paired with a
software cartridge.

**Repository layout** — `python tests/run_ci.py` is green ✅ (16 protocol checks + ROM + firmware + case builds)
- [`WORKBOY_PROTOCOL.md`](WORKBOY_PROTOCOL.md) — link protocol + scan-code table (the shared contract)
- [`layout/`](layout/keymap.py) — **single source of truth** for the 53-key layout; `gen_layout.py` emits the firmware scancode header, [`keymap.svg`](layout/keymap.svg), case positions, and PCB placement
- `firmware/` — ATmega328P firmware ([`workboy_keyboard.c`](firmware/workboy_keyboard.c)) + PlatformIO. **Builds ~1.3 KB flash (avr-gcc).**
- `rom/` — clean-room GBDK cartridge: notepad + **clock w/ set** + **calculator** + **phone book (32 KB battery SRAM)**. **Builds 128 KB MBC1+RAM+BAT.**
- `kicad/` — netlist + **DRC-clean routed board** ([`workboy.kicad_pcb`](kicad/workboy.kicad_pcb), 0 violations), **Gerbers** (`gerber/` / `workboy_gerbers.zip`), **CPL** ([`workboy_cpl_jlcpcb.csv`](kicad/workboy_cpl_jlcpcb.csv)); pipeline in [`PCB_README.md`](kicad/PCB_README.md)
- `case/` — [`OpenSCAD`](case/workboy_case.scad) + [`build123d`](case/workboy_case_b123d.py) enclosures (real key layout; export STL/STEP, import the board STEP)
- [`workboy_jlcpcb_bom.csv`](workboy_jlcpcb_bom.csv) — assembly BOM · [`SHOPPING_LIST.md`](SHOPPING_LIST.md) — what to buy · [`EMULATOR_VALIDATION.md`](EMULATOR_VALIDATION.md) — validate vs the real ROM
- `tests/` — [`protocol_sim.py`](tests/protocol_sim.py) (16 checks) + [`run_ci.py`](tests/run_ci.py); CI in [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

> **Sourcing note:** the `tcrf.net/Workboy` web page currently serves a
> prompt-injection test (fake "delete files / run commands" text) to automated
> fetchers. It was ignored. Factual content here comes from the clean TCRF PDFs
> you supplied plus primary sources (gbdev Pan Docs, shonumi's GBE+/Dan Docs,
> SameBoy, JLCPCB/LCSC). Verify the cited LCSC part numbers at order time —
> stock and IDs change.

---

## 1. How the real WorkBoy worked (and what that means we must build)

The WorkBoy is a **two-part system**:

1. A **software cartridge** (the leaked dump is `DMGWYE-0.781`, game code "WYE",
   SHA-256 `8C365C…BC45E`) that runs the 12 productivity apps (clock, calculator,
   phone book, calendar/diary, thermometer, unit & currency conversion,
   accounts, translator across 5 languages, world map, phone auto-dialer).
   **Header confirmed by reading the ROM:** title `WORKBOY`, **DMG-only**,
   cartridge type **`0x03` = MBC1 + RAM + BATTERY**, **128 KiB ROM**, **32 KiB
   (4 × 8 KiB) battery-backed SRAM** — all user data lives in that battery SRAM.
2. An external **QWERTY keyboard** (~146 × 89 mm / 5¾″ × 3½″) with its own
   **real-time clock and battery**, connected to the **Link Port** as a serial
   **slave**. The Game Boy is the **master**: it clocks the link and polls the
   keyboard; the keyboard returns one scan-code byte per poll.

The protocol is fully documented (shonumi reverse-engineered it into GBE+ and
SameBoy) — see [`WORKBOY_PROTOCOL.md`](WORKBOY_PROTOCOL.md). Four commands:
`0x52` Init→`0x44`, `0x4F` Poll→scancode, `0x44` Read-RTC→42 bytes,
`0x57` Write-RTC→`0x30`+data. **The clock the calendar/clock apps read comes from
the keyboard's RTC over the link, not from the cartridge.**

### Our recreation = three buildable subsystems

| Subsystem | What it is | This plan |
|---|---|---|
| **A. Keyboard controller PCB** | An MCU that scans a ~53-key matrix and answers the link protocol as a slave | §3 PCB, §4 components, §6 firmware |
| **B. Software cartridge** | The `.gb` that drives the protocol and runs the apps | §2 ROM |
| **C. Enclosure** | 3D-printed case + keycaps housing the PCB | §5 case |

---

## 2. ROM strategy

You have two paths. Pick based on whether this stays **personal** or gets
**shared/sold**.

### Path A — Personal build: leaked ROM on a flash cart (fastest, what Robertson did)
The leaked `DMGWYE-0.781` build is the *only known working binary*, and burning it
to a flash cart is exactly how the original prototype was demonstrated in 2020.
- **Dev/run cart:** an **EverDrive GB (X5/X7)** or **EZ-Flash Junior** — microSD,
  drag-and-drop `.gb`, pick from a menu. Handles MBC banking + battery SRAM saves,
  so it imposes no constraints. To run the raw leak file, append `.gb` to the
  filename so emulators/flashers recognise it.
- **Legal reality:** the ROM is leaked, copyrighted Nintendo-licensed code.
  Possessing/running it privately is one thing; **distributing it is copyright
  infringement.** Do not ship it, host it, or include it with a product.

### Path B — Distributable build: clean-room homebrew ROM (the legal product path)
Write your own cartridge software in **GBDK-2020** that speaks the same four-command
protocol. Because the protocol is small and documented, this is very tractable.
- Derive from the **protocol description** (`WORKBOY_PROTOCOL.md` / Dan Docs),
  **not** from disassembling the leaked binary — otherwise it's a derivative work.
- A clean-room app suite *could* be smaller, but to match the original's
  save-everything database (phone book 140 B/entry, appointments 66 B/entry) you
  need battery SRAM. Plan for **MBC1 + RAM + BATTERY** (the original is 128 KiB
  ROM / 32 KiB battery SRAM); only drop to ROM-ONLY 32 KB if you cut persistent
  saves entirely.
- **Biggest advantage:** since you own *both* ends, you also resolve every
  disputed protocol detail (no-key value, modifier model, RTC-write length) by
  fiat — just implement the same choice in firmware and ROM.

### Optional Path C — Fab your own cartridge hardware
To run the **original** ROM you need an **MBC1 cart: 128 KiB flash + an MBC1
mapper + 32 KiB SRAM + a coin cell** for save retention (a no-MBC 32 KB cart
*won't* run it — the ROM is 128 KiB and banks its SRAM). Easiest is a blank
"MBC1+RAM+BAT" repro/donor cart, or an MBC1 PCB with an SST39SF-class 5 V flash,
a 62256/HM62256 32 KB SRAM, and a CR2032. Only a clean-room ROM that drops
persistent saves could use the trivial no-mapper 32 KB design. Panelize whichever
cart with the keyboard PCB to share one JLCPCB setup fee.

**Recommendation:** bring up the hardware against **Path A privately**, ship with
**Path B**. Keep an EverDrive on the bench throughout for A/B debugging.

---

## 3. Custom PCB (keyboard controller)

### 3.1 Core decision — a 5 V-native MCU, so **no level shifter**
The DMG/GBC link is **5 V TTL**. An **ATmega328P-AU** runs natively at 5 V, reads
the GB's 5 V HIGH directly (V_IH = 0.6·VCC = 3.0 V), and its hardware **SPI slave**
is guaranteed to fosc/4 (≥2 MHz) — ~250× the GB's 8192 Hz clock. That collapses
three problems at once: **no TXS0108/BSS138 translator, no second logic rail, no
timing risk.** (A 3.3 V RP2040 is *not* 5 V-tolerant — abs-max ~3.63 V — and would
need inbound level shifting; we avoid that entirely.)

> Verified caveat: "no translator IC" ≠ "zero extra parts." Still mirror the Game
> Boy's own link protection — **220 Ω series resistors** on SO/SI/SC and a defined
> idle level — because a disconnected GB serial input floats HIGH over ~20 µs.

### 3.2 Schematic blocks

```
            GB DMG/GBC LINK (5V TTL, GB = MASTER/clock)
   J1: 1=VCC(NC)  2=SO   3=SI   4=SD(NC)   5=SC    6=GND
                   |      |                 |       |
                 220R    220R             220R      |
                 (R4)    (R5)             (R6)       |
                   v      ^                 v        v
              MOSI(PB3)  MISO(PB4)        SCK(PB5)  GND
              [sample]   [drive]          [clk in]  plane
                   \      |                 /
                    +--- ATmega328P-AU (U1, 5V, int. 8MHz RC) ---+
   USB-C 5V --SS14--+--> VCC/AVCC (+100nF x4, +10uF x2)          |
   (J3)  CC 5k1 x2  |    /SS(PB2) -> 10k -> GND (always selected) |
                    |    /RESET(PC6) -> 10k pull-up               |
                    |    ROW0..7  (8 GPIO, open-drain drive) -----+--+
                    |    COL0..6  (7 GPIO, input + pull-up) ---+  |  |
                    |    LED1/2/3 -> 1k -> {power, CAPS, NUM}  |  |  |
                    |    ISP J2 (MISO/MOSI/SCK/RST/VCC/GND)    |  |  |
                    +-----------------------------------------|--|--+
                                                              |  |
                 8x7 DIODE MATRIX (53 keys populated)         |  |
        ROWn --[SWxx]--|>|--(D 1N4148W)--> COLm  <------------+--+
        (drive ROW low, read COL; one diode/key = N-key rollover)
```

**Block list**
- **U1** ATmega328P-AU, internal 8 MHz RC (no crystal → frees PB6/PB7 as GPIO).
- **Decoupling** 4×100 nF (VCC, AVCC, AREF, reset) + 2×10 µF bulk; 10 k on /RESET.
- **Matrix** 8 rows × 7 cols = 56 cells, **53 populated** (one key per scan code).
  One **1N4148W** steering diode per key (anode at switch, cathode to column) →
  full N-key rollover / no ghosting. Rows driven LOW one at a time; columns read
  with the AVR's **internal pull-ups** (so no external column resistors).
- **Link interface** 3×220 Ω series on SO/SI/SC; `/SS` strapped low (single slave).
- **Power** USB-C 5 V in → SS14 Schottky → 5 V rail → VCC (no LDO; AVR is 5 V).
  2×5.1 k CC resistors for USB-C sink. (Battery/coin-cell can OR onto the rail.)
- **Programming** 2×3 ISP header (J2). ISP shares the SPI pins with the link —
  **program before attaching the link cable.**
- **Status LEDs** power + CAPS + NUM (optional).
- **Link connector** J1 — see §4 (no catalog part; cut cable or breakout PCB).

### 3.3 Pin budget (it closes exactly)
ATmega328P-AU digital GPIO = 18 after SPI (PB2–5) and /RESET are reserved
(PB0,1,6,7 + PC0–5 + PD0–7). Matrix 8+7 = **15**, status LEDs = **3** → **18/18**.
Zero spare — if you want a hardware RTC chip (I²C, for battery-backed timekeeping)
or more I/O, drop a status LED or a key row, or add an I²C port expander.

### 3.4 Board
- **2-layer FR-4, 1.6 mm, 1 oz.** No impedance control needed at 8 kHz.
- **Size: 152.000 × 106.125 mm** — *measured from `Edge.Cuts` in
  `kicad/workboy.kicad_pcb` on 2026-07-28, superseding the earlier ~140 × 85 mm
  estimate.* Area **161.31 cm²**. Outline driven by the key field at ~10 mm pitch
  to match the original's footprint; PCB tucks under the top plate.
  ⚠️ **Over JLCPCB's ≤100 × 100 mm bracket on both axes** — the cheap price tier in
  §Cost does not apply. See `PREFAB_CHECKLIST.md` §5.
- ⚠️ **4× M2.5 corner mounts are specified here but are NOT on the board** — it
  currently has zero mounting holes. Blocking; see `PREFAB_CHECKLIST.md` §1.
  (+1 center boss if the plate spans >120 mm.)
- **Design-for-assembly:** all SMT (U1, passives, 53 diodes, LEDs, USB-C) on the
  **top side only** → one reflow pass → JLCPCB **Economic** single-sided placement.
  Only THT parts = 53 tact switches + ISP header + link connector.

---

## 4. Components / BOM

The assembly-ready file is [`workboy_jlcpcb_bom.csv`](workboy_jlcpcb_bom.csv)
(JLCPCB columns: `Comment, Designator, Footprint, LCSC Part #`). Summary:

| Function | Part | Pkg | LCSC | Tier | Qty |
|---|---|---|---|---|---|
| MCU (5 V SPI slave) | ATmega328P-AU | TQFP-32 | **C14877** | Extended | 1 |
| Decoupling | 100 nF | 0402 | C1525 | Basic | 4 |
| Bulk | 10 µF | 0805 | C15850 | Basic | 2 |
| Key diodes (NKRO) | 1N4148W | SOD-123 | **C2099** | **Basic** | 53 |
| Schottky (USB rev.) | SS14 | SMA | C2480 | Basic | 1 |
| 10 k (reset + SPI pull-ups) | 10 kΩ | 0402 | C25744 | Basic | 3 |
| 220 Ω (link series) | 220 Ω | 0402 | C25091 | Basic | 3 |
| 1 k (LED series) | 1 kΩ | 0402 | C11702 | Basic | 3 |
| 5.1 k (USB-C CC) | 5.1 kΩ | 0402 | C25905 | Basic | 2 |
| Power LED | Red | 0805 | C2286 | Basic | 1 |
| CAPS/NUM LEDs | Green | 0805 | C72043 | Ext-Preferred | 2 |
| USB-C power | TYPE-C 16P | SMD | C165948 | Ext-Preferred | 1 |
| **Tactile switch (THT)** | 6×6 mm tact | TH | C720477 | Ext-THT | 53 |
| ISP header (THT) | 2×3 2.54 mm | TH | C2718 | Ext-THT | 1 |
| **Link connector** | GB EXT — **consign / cut cable** | — | none | Consign | 1 |

**Why these choices keep assembly cheap**
- Only ~3–4 *unique extended* SMT lines (MCU, USB-C, green LED) → well under the
  ~17-part crossover where JLCPCB Standard beats Economic. Each unique extended
  part is ~$3 on Economic.
- The two huge lines — **53×1N4148W (Basic)** and **4×100 nF (Basic)** — incur **no
  feeder fee.**
- **THT is the cost driver:** 53 tact switches via JLCPCB's PTH service add a
  $3.50 labor fee + per-joint + a possible per-unique-part fee. **Strongly
  consider hand-soldering the 53 switches + connector yourself** and letting
  JLCPCB do only the SMT side — tact switches are the easiest possible hand-solder.
- The **link connector has no modern catalog part.** Cut a genuine DMG/MGB/CGB
  link cable into a pigtail, or use a Palmr/vaguilar-style edge breakout. It is
  excluded from the CSV (consign it or hand-solder) — wire J1 as: 2=SO, 3=SI,
  5=SC, 6=GND (pins 1 VCC / 4 SD unused). Stock cables only carry 4 of 6 pins,
  which is fine since we're self-powered.

> **Not in the recommended build (documented for variants):** a 3.3 V design would
> add a **TXS0108E** level shifter (C17206) + **AMS1117-3.3** (C6186) / **ME6211**
> (C82942) LDO. A precision RTC could add a DS3231/PCF8563 on I²C with a coin cell.

---

## 5. 3D-printed case

Clean-sheet enclosure (the original's internals were never photographed), built
around the locked parts: 53 6×6 mm THT switches, the controller PCB, and a link
pigtail.

- **Form factor:** landscape slab **~140–155 × 75–90 × 18–24 mm**, two-piece
  clamshell — **top plate** with key cutouts + **bottom shell** with PCB, power,
  and cable exit. Support both a **clip-on cradle** (snaps under a DMG, like the
  original) as a *separate* bolt-on accessory, and **standalone** rubber feet with
  a 3–6° typing wedge.
- **Key interface:** floating keycaps **captured by the top plate** (square hole
  ~1.0–1.5 mm larger than the cap skirt on FDM) ride the switch plunger — far less
  rattle than gluing caps to plungers. **~10 mm key pitch.** Plate 1.6–2.5 mm.
- **Structure:** **M2/M2.5 brass heat-set inserts** (not self-tappers — you'll
  open this a lot during bring-up). Boss OD ≈ 2× insert OD; gusset fillets to the
  floor. PCB located in X/Y by two diagonal pegs, in Z by standoffs (leave 3–4 mm
  under the board for clipped THT lead tails).
- **Cable:** exit on the rear edge with real strain relief (printed C-clamp /
  serpentine + internal anchor or grommet). Simplest is a soldered pigtail from a
  cut link cable; optional internal 6-pin JST makes it serviceable.
- **Materials:** **PETG** for the body (tougher/more heat-tolerant than PLA;
  survives heat-set inserts and a warm console). **Resin** for crisp keycaps with
  legends — the WorkBoy legends (QWERTY + 9 app keys + CAPS/NUM + arrows + the
  NUM-mode symbols) are non-standard, so off-the-shelf caps won't have them; buy
  blank caps + printed legend overlays, or resin-print custom caps.
- **CAD:** parametric/code-CAD (Fusion 360 / FreeCAD / Onshape / OpenSCAD /
  build123d). Import the **KiCad board outline + switch/mount positions (STEP/DXF)**
  and build the case around it so plate holes, standoffs, and cable exit line up
  with the real board. Drive everything from master params: `key_pitch`,
  `rows`/`cols`, the vertical stack-up (`plate_thickness` + `standoff_height` +
  `switch_height` + `keycap_height` must close), and the tolerance knobs
  (`keycap_clearance`, `snap_interference`, `insert_hole_dia`). **Print a one-row
  fit-test coupon before the full 53-key print.**
- **Tolerances:** FDM 0.15–0.30 mm slop, holes modeled ~0.2–0.4 mm oversize,
  snap fits 0.3–0.4 mm interference. Resin 0.05–0.15 mm; calibrate cap shrinkage
  with a coupon.

---

## 6. Firmware

Skeleton: [`firmware/workboy_keyboard.c`](firmware/workboy_keyboard.c) (avr-gcc /
PlatformIO). Architecture:
- **Hardware SPI slave** (Mode 1: CPOL=0, CPHA=1, MSB-first) services the link
  entirely inside the `SPI_STC` ISR via the four-command state machine — stage one
  response byte per received command (response to byte *N* is consumed on *N+1*).
- **1 ms Timer0** tick runs a row-by-row matrix scan with a 4-sample debounce
  integrator; on a confirmed press it latches the scan code into a 1-deep
  "most-recent key" register (the protocol returns only one key per poll) with
  report-once repeat suppression.
- **Timer1 1 Hz** software RTC formats the 42-byte read buffer in BCD on demand.
- Keep the ISR tiny (just stage bytes); never scan or format inside it.
- `WORKBOY_NOKEY`, the modifier model, and the RTC-write length are `#define`s so
  you can flip GBE+↔SameBoy conventions if real-hardware testing disagrees.
- **Validate the edge convention on a logic analyzer** — if the Init reply comes
  back rotated, flip CPHA to Mode 3.

Fill in two things once the PCB is laid out: the `SCANCODE[ROWS][COLS]` table
(map each matrix cell to its protocol code) and the `drive_row()`/`read_col()`
GPIO mapping.

---

## 7. Manufacturing with JLCPCB / PCBWay

### Deliverables
| File | JLCPCB format |
|---|---|
| **Gerbers** | RS-274X, zipped |
| **BOM** | CSV: `Comment, Designator, Footprint, LCSC Part #` — [`workboy_jlcpcb_bom.csv`](workboy_jlcpcb_bom.csv) |
| **CPL / centroid** | CSV: `Designator, Mid X, Mid Y, Rotation, Layer` (mm, Top/Bottom) — **generated from the PCB layout, not yet created** |

> ⚠️ The CPL/centroid and the Gerbers **require an actual PCB layout** (schematic →
> KiCad layout). The BOM here is the *design* BOM; its designators are provisional
> and must be reconciled with the final schematic. Designators are case-sensitive
> and must match exactly between BOM and CPL.

### Vendor pick & cost levers
- **JLCPCB Economic PCBA** is cheapest for this SMT-heavy, single-sided board:
  ~$8 setup + $1.50 stencil + ~$0.0017/joint + $3/unique extended part. Boards
  down to 10×10 mm; min 2–5 boards.
- Keep it cheap: single-sided placement, **Basic + Preferred-Extended parts**,
  minimal unique-extended lines, panelize small boards to share one setup fee.
- **THT** is supported (wave/hand-solder, +$3.50 labor + per-joint + possible
  per-part fee) — but for **53 switches, hand-solder them yourself.**
- **PCBWay** is the better choice if you want full turnkey THT or to **consign**
  the link connector and switches; it explicitly supports SMT + THT + hybrid.

---

## 8. Bring-up & testing (retire risk on cheap hardware first)

1. **P0 — Emulator:** validate firmware byte-responses against **GBE+** / **SameBoy**
   (host keyboard stands in). Catches protocol-logic bugs for $0.
2. **P1 — Breadboard:** ATmega + cut link cable + logic analyzer. Confirm
   `0x52`→`0x44` Init and a scan code on `0x4F`, **first on the analyzer** (decode
   SPI: MSB-first, 8-bit, idle-low, sample-on-rising), then on a real Game Boy.
   This is the **non-negotiable gate before any PCB spend** — it converts the only
   real unknown (the under-documented protocol) into a solved problem.
3. **P2 — Perfboard matrix:** wire real switches + diodes; walk the whole
   scan-code table; confirm CAPS/NUM toggles flip interpretation; RTC round-trips.
4. **P3 — PCB rev A:** fab + (self-)assemble + printed case; full end-to-end on a
   real DMG with the ROM.
5. **P4 — Small batch:** panelized run; every unit passes the same end-to-end test.

**Top failure modes:** off-by-one response staging; wrong SPI edge (CPOL/CPHA);
no-key value mismatch (`0x00` vs `0xFF`); reversed SI/SO on the cut cable
(meter-check before connecting!); missing per-key diodes → ghosting; powering from
the link VCC pin (don't).

---

## 9. Cost & lead time (order-of-magnitude, USD, excludes the Game Boy)

| | First unit | Small batch (10–25) |
|---|---|---|
| Bare PCB (5-pc min, <100 mm) | ~$7–17 (gets you 5) | ~$2–4/board equiv. |
| SMT assembly (Economic) | ~$15–35 | ~$5–12/board |
| Parts (MCU, 53 sw, 53 diodes, passives, USB-C) | ~$10–20 | ~$8–15/unit |
| Flash cart (reusable) | ~$30–60 once | — |
| Case + 53 keycaps (self-printed) | ~$2–5 filament | cheaper/unit |
| Tooling (logic analyzer + ISP programmer) | ~$15–40 once | — |
| **Per-unit incremental** | **~$30–60** | **~$25–45** |
| **First unit all-in (w/ tooling + cart)** | **~$120–200** | — |

**Lead time:** PCB fab + Economic SMT ~5–10 business days (+~1 day if JLCPCB
hand-solders THT); case prints in hours; firmware/ROM in minutes. First working
unit ≈ **1.5–2.5 weeks** once P0–P2 are validated on breadboard.

---

## 10. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Protocol details disputed (no-key `0x00`/`0xFF`, modifier model, RTC-write len) | High | High | We own both ends → lock GBE+ convention; `#define` to flip; verify vs real ROM |
| R2 | ROM legality (leak not distributable) | Certain for distribution | High | Leak = private bring-up only; ship clean-room GBDK ROM |
| R3 | 3.3 V MCU killed by 5 V link | High *if* RP2040 | High | Use 5 V ATmega328P (chosen) → no shifter |
| R4 | SPI edge / off-by-one staging | Med | Med | HW SPI slave; verify on logic analyzer at P1 |
| R5 | No catalog link connector; pinout error | Med | Med | Cut official cable or breakout; meter-check SI/SO/SC |
| R6 | ~~Mapper/RAM unknown~~ **resolved** | — | — | ROM header read: **MBC1+RAM+BATTERY, 128 KiB ROM, 32 KiB battery SRAM** — cart must provide this for the original ROM |
| R7 | THT assembly cost on 53 switches | Med | Low-Med | Hand-solder switches; PCBA only the SMT side |
| R8 | Exact original key count only seen in video | Med | Low | Lay matrix to the **scan-code map** (53), not a guessed physical layout |
| R9 | LCSC part IDs go out of stock | Med | Low | Re-verify every LCSC # at order time |

---

## 11. Next actions (recommended order)

1. **Breadboard P0/P1** — flash [`firmware/workboy_keyboard.c`](firmware/workboy_keyboard.c)
   onto an ATmega328P (an Arduino Uno is fine), wire a cut link cable, and prove
   the Init handshake + a key on a real Game Boy with the ROM on an EverDrive.
2. ~~KiCad netlist~~ ✅ **done** — [`kicad/workboy.net`](kicad/workboy.net) +
   [`kicad/KICAD_NETLIST.md`](kicad/KICAD_NETLIST.md). Next: import into the KiCad
   PCB editor → **lay out** (152.000 × 106.125 mm as built, top-side SMT, 8×7 switch grid) → export
   **Gerbers + CPL**. (Verify the J3 USB-C and J1 link footprints first — see the
   netlist doc §4.)
3. **Case** — import the board outline, model the parametric clamshell, print a
   fit-test coupon.
4. **Order** — JLCPCB Economic (SMT only), hand-solder switches + link pigtail.
5. **Clean-room ROM** in GBDK-2020 if you intend to distribute.

I can take the next concrete step for you — e.g. scaffold the **KiCad project +
netlist** from this schematic, flesh out the **firmware GPIO/scan map**, or start
the **GBDK ROM skeleton**. Say which and I'll build it.

---

## 12. Sources

**WorkBoy history / ROM** — Video Game History Foundation (gamehistory.org),
Inverse, TechSpot, Time Extension, TheGamer, Retro Reversing (lot-check leak),
plus your TCRF PDFs.
**Protocol** — shonumi GBE+ `WorkBoy.txt` + `src/dmg/sio.cpp`; SameBoy
`Core/workboy.c`/`.h`; gbdev Pan Docs (Serial Data Transfer / External Connectors);
Dhole's STM32 serial-sniffing writeup (SPI mode/5 V TTL).
**Electrical / connector** — gbdev Pan Docs, Wikipedia Game Link Cable, Nerdly
Pleasures (cables carry 4/6 pins), Palmr & vaguilar link breakouts.
**MCU / parts** — ATmega328P datasheet; LCSC/JLCPCB part library.
**Assembly** — JLCPCB BOM/CPL & PCBA pricing help pages; PCBWay assembly file
requirements.
