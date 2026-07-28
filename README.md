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
