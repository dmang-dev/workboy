# WorkBoy keyboard firmware (ATmega328P)

Bare-metal AVR firmware that makes the controller PCB act as the WorkBoy
keyboard: a passive **SPI slave** on the Game Boy link, plus an 8×7 matrix scan.
Protocol contract: [`../WORKBOY_PROTOCOL.md`](../WORKBOY_PROTOCOL.md). Pin map:
[`../kicad/KICAD_NETLIST.md`](../kicad/KICAD_NETLIST.md).

## Pin map (matches `kicad/workboy.net`)
- **Rows** ROW0–7 = **PORTD** (PD0–PD7) — driven LOW one at a time, others hi-Z.
- **Cols** COL0–5 = PC0–PC5, COL6 = PB0 — inputs with internal pull-ups.
- **Link SPI** /SS PB2, MOSI PB3, MISO PB4, SCK PB5 (Mode 1, MSB-first).
- **LEDs** PB6 (CAPS), PB7 (NUM). **Reset** PC6. **Spare** PB1.

## Build / flash (PlatformIO)
```sh
pio run            # build
pio run -t fuses   # internal 8 MHz RC + BOD 2.7 V (needed so PB6/PB7 are GPIO)
pio run -t upload  # flash via USBasp on the ISP header (J2)
```
Program **before** attaching the link cable — the ISP pins are shared with the
link SPI lines.

No PlatformIO? Build with avr-gcc directly:
```sh
avr-gcc -mmcu=atmega328p -DF_CPU=8000000UL -Os -Wall -o workboy.elf workboy_keyboard.c
avr-objcopy -O ihex workboy.elf workboy.hex
avrdude -c usbasp -p m328p -U flash:w:workboy.hex
# fuses: internal 8 MHz, BOD 2.7 V
avrdude -c usbasp -p m328p -U lfuse:w:0xE2:m -U hfuse:w:0xD9:m -U efuse:w:0xFD:m
```

## What to verify on first bring-up
1. **SPI edge:** the code uses Mode 1 (CPOL=0, CPHA=1). If the Init reply comes
   back rotated on a logic analyzer, flip `CPHA` (see `spi_slave_init`) to Mode 3.
2. **No-key value & modifier model:** `WB_NOKEY` and the toggle-vs-shift model are
   `#define`s at the top of `workboy_keyboard.c`. Defaults match the GBE+/leaked-ROM
   convention; flip to SameBoy's (`0xFF`, held-shift) only if the real ROM rejects
   input.
3. **Matrix:** fill `SCANCODE[ROWS][COLS]` to your physical key wiring; the diode
   orientation (anode→COL) must match the scan direction (drive ROW low, read COL).

## Status
`workboy_keyboard.c` is complete and self-contained: SPI-slave state machine,
1 ms debounced matrix scan, 1 Hz software RTC, and the GPIO layer wired to the
netlist. The two things to finalize per your build are the physical `SCANCODE`
legend map and (optionally) lighting the CAPS/NUM LEDs.
