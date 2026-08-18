# WorkBoy — a modern, buildable recreation

An open recreation of Nintendo's unreleased **Game Boy WorkBoy** keyboard
accessory (Source R&D / Fabtek / Montague‑Weston, 1992): a QWERTY keyboard that
plugs into the Game Boy Link Port and turns the console into a PDA, plus a
software cartridge.

This repo contains a complete, **buildable and CI‑verified** design — firmware,
a clean‑room ROM, a DRC‑clean PCB, a 3D‑printed case, and an assembly‑ready BOM.

> **Status:** `python tests/run_ci.py` is green — 16 protocol checks + ROM,
> firmware, and case builds. The PCB autoroutes to **0 DRC violations**.

## What's here
| Path | What |
|---|---|
| [`BUILD_PLAN.md`](BUILD_PLAN.md) | the full engineering plan (start here) |
| [`WORKBOY_PROTOCOL.md`](WORKBOY_PROTOCOL.md) | the link‑port byte protocol + scan‑code table |
| `layout/` | single source of truth for the 53‑key layout (`keymap.py`) |
| `firmware/` | ATmega328P keyboard firmware (PlatformIO / avr‑gcc) |
| `rom/` | clean‑room GBDK cartridge: notepad, clock, calculator, phone book |
| `kicad/` | netlist, placed+routed board, Gerbers, CPL — see [`PCB_README.md`](kicad/PCB_README.md) |
| `case/` | parametric enclosure (OpenSCAD + build123d) |
| `tests/` | `protocol_sim.py` + `run_ci.py`; CI in `.github/workflows/` |

## Build & test
```sh
python tests/run_ci.py     # runs every check whose toolchain is installed
```
Toolchains: GBDK‑2020 (ROM), PlatformIO + avr‑gcc (firmware), build123d (case),
KiCad 10 + Freerouting (PCB). See [`BUILD_PLAN.md`](BUILD_PLAN.md) and
[`kicad/PCB_README.md`](kicad/PCB_README.md) for the full pipelines.

## How it works (one paragraph)
The Game Boy is the serial master on the link port; the WorkBoy keyboard is a
passive slave that returns one scan‑code byte per poll. So the "custom PCB" is a
small **5 V ATmega328P keyboard‑matrix controller** that speaks the documented
WorkBoy serial protocol — no level shifter needed. The protocol/scan‑codes were
reverse‑engineered by shonumi (GBE+) and re‑verified here against the real ROM.

## Console compatibility

**One 5 V design covers every console that can run a Game Boy / Game Boy Color
cartridge** — including the GBA and GBA SP, whose link port switches to **5 V**
when an 8‑bit cartridge is inserted. Only the cable plug varies.

| Works | Doesn't |
|---|---|
| DMG‑01, Pocket, Light, Color, GBA, GBA SP | **Game Boy Micro** (GBA‑only, can't run GB/GBC carts) · **Super Game Boy** (no link port) |

Full table, cable choices, and why this is **not** split into per‑console repos:
[`COMPATIBILITY.md`](COMPATIBILITY.md).

> ⚠️ GBA/SP support is documented behaviour that this project has **not yet
> verified on a bench**. Measure before trusting it.

## What you'll need to build one

Nothing here is exotic. Rough 2026 USD; the board is most of the cost.

**Console side**
| Item | Why | ~$ |
|---|---|---|
| A Game Boy that runs GB/GBC carts | the target console — see the compatibility table above | — |
| Flash cart + microSD (EZ-Flash Junior, EverDrive GB, …) | runs `rom/workboy_homebrew.gb`. SD-backed saves mean the phone book persists with **no cart battery** | 25–70 |
| A cheap DMG/GBC link cable to cut | the plug end *is* the connector — see below | 5–8 |

**The keyboard board**
| Item | Why | ~$ |
|---|---|---|
| Bare PCB from JLCPCB, qty 10 | zip up `kicad/gerber/` and upload it. ~$19.60 + shipping | 48 |
| Components per [`workboy_jlcpcb_bom.csv`](workboy_jlcpcb_bom.csv) | one 100-pc lot of each resistor value covers the run. The ATmega is 55 % of it | 39 |
| ~60× 6×6 mm THT tact switches (LCSC **C42416249**) | the 53 keys + spares. ⚠️ *Not* C720477 — that is an SMD 4×3 mm part and will not fit | 2 |
| 2×3 2.54 mm pin header | the ISP header (J2), for flashing | 1 |
| M2.5 brass heat-set inserts + screws | fasten the printed clamshell | 10 |
| *(optional)* blank tactile keycaps | nicer than printed; legends are non-standard anyway | 6 |

Ordering **10 boards** costs $86.50 all-in ($8.65/board) versus $59.75 for 5 —
28 % cheaper per board, because the engineering fee and shipping don't scale.

**Tools**
- **An ISP programmer.** An **Arduino Uno running the stock ArduinoISP sketch** is
  the cheapest route and doubles as the breadboard prototype MCU (it's a 5 V
  ATmega328P, so it talks to the DMG link directly). A USBasp works too.
  ⚠️ **An ST-Link will not work** — it speaks SWD/JTAG/SWIM, and the ATmega needs
  ISP. `firmware/platformio.ini` already ships a commented `stk500v1` block for
  the Arduino-as-ISP path.
- **A logic analyzer** (any cheap 8-channel 24 MHz sigrok/PulseView clone, ~$10) —
  verifying the SPI handshake and clock edge is the single most useful bring-up check.
- Soldering iron, solder, flux · breadboard + dupont wires · 3D printer + PETG/PLA.

**The link connector — the one part with no catalog option**
There is no reliably-purchasable bare DMG link plug. Either **cut a third-party
link cable** (most reliable — keep the 4 used wires SO/SI/SC/GND, and *meter them
before soldering*: the two ends are deliberately cross-wired, so one end's SO is
the other's SI), or **3D-print the plug** — e.g. svender's
[DMG link cable plug](https://www.thingiverse.com/thing:6924711), which uses 6 pins
harvested from female USB sockets. Breakout PCBs exist but still need a cable.

**Suggested order of purchase.** Buy the logic analyzer and a link cable first and
run the P0/P1 protocol test on a breadboard — prove the handshake before spending
on the PCB. Order boards, switches and inserts only once that works.

## Licence

**MIT** — see [`LICENSE`](LICENSE). Attribution, scope, and what is deliberately
*not* in this repo are recorded in [`NOTICE`](NOTICE).

## Legal

This is an independent, unofficial recreation. It is **not affiliated with,
endorsed by, or connected to Nintendo**, Source R&D, Fabtek, or Montague‑Weston.
"WorkBoy" and "Game Boy" are used descriptively to identify the device being
recreated and the consoles it attaches to.

The original WorkBoy ROM is leaked, copyrighted Nintendo‑licensed code — it is
**not** included here and must not be committed or distributed. The cartridge
software in `rom/` is **clean‑room**, written from the documented wire protocol.
Use the leaked ROM only for private bench reference.

The WorkBoy trademark (USPTO 74239332, filed 1992) was **abandoned in 1994**
without ever registering, and both original companies are defunct — see
[`NOTICE`](NOTICE).
