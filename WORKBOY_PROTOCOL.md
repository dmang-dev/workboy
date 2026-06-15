# WorkBoy ↔ Game Boy Link Protocol Reference

This is the byte-level contract our keyboard firmware must implement and our ROM
must speak. It is reverse-engineered from the leaked WorkBoy ROM behaviour by
**shonumi (D.S. Baxter)** and reimplemented independently in two emulators. Treat
these as the authoritative references:

- shonumi GBE+ — prose: `src/docs/technical/WorkBoy.txt`; implementation:
  `src/dmg/sio.cpp` (`workboy_process`, `WORKBOY_*` states)
  <https://github.com/shonumi/gbe-plus>
- SameBoy — `Core/workboy.c` / `Core/workboy.h`
  <https://github.com/LIJI32/SameBoy/blob/master/Core/workboy.c>
- Game Boy serial fundamentals — gbdev Pan Docs (Serial Data Transfer / External
  Connectors) <https://gbdev.io/pandocs/Serial_Data_Transfer_(Link_Cable).html>

> ⚠️ The two emulator reimplementations **disagree** on a few details (see
> "Disputed details"). Because *we* write both ends (firmware **and** ROM), we
> pick one convention and implement it identically on both. This document locks
> the **GBE+/Dan Docs convention**, because that is the behaviour the leaked ROM
> driver was matched against — so it also works if you bring up against the
> leaked ROM as a private reference.

---

## 1. Electrical / framing

| Property | Value |
|---|---|
| Topology | **Game Boy = serial MASTER** (internal clock, drives `SC`). Keyboard = passive **SLAVE**. |
| Clock pin | `SC` (link pin 5). Idles **LOW**. |
| Bit order | **MSB-first**, 8 bits per transfer. |
| SPI mode | Mode 1-like per Dhole: slave updates output on **SCK falling edge**, master samples on **rising edge** (CPOL=0, CPHA=1). *Validate on a logic analyzer; flip CPHA to Mode 3 if the first byte is off by one edge.* |
| Clock rate | DMG fixed **8192 Hz** (~122 µs/bit, ~977 µs/byte). CGB may use 16384 Hz; external slave tolerated to ~500 kHz. |
| Logic level | **5 V TTL** on DMG/GBC (3.3 V on GBA — out of scope). |
| Exchange | Full-duplex: every transfer shifts one byte out **and** one byte in. The keyboard returns its response to command *N* **during transfer *N+1*** (pipeline by one). Pre-load `0x00` at startup so the first exchange is safe. |

The keyboard **never** drives the clock and **never** initiates a transfer.
(This is the conventional configuration — the *opposite* of the Barcode Boy,
which forces the Game Boy into slave mode.)

---

## 2. The four commands (all sent by the Game Boy)

| GB sends | ASCII | Meaning | Keyboard must reply |
|---|---|---|---|
| `0x52` | `'R'` | **Init / handshake** | `0x44`, then enter ACTIVE state |
| `0x4F` | `'O'` | **Poll keyboard** | one byte = scan code of most-recent key (`0x00` = none) |
| `0x44` | `'D'` | **Read RTC** | stream of **42** bytes (time/date) |
| `0x57` | `'W'` | **Write RTC** | `0x30`, then absorb ~**23–24** bytes from GB |

Reference state machine (from GBE+ `sio.cpp`):

```
IDLE:   if cmd==0x52 -> reply 0x44, state=ACTIVE      else reply 0x00
ACTIVE: cmd==0x4F -> reply current_scancode (then mark consumed)
        cmd==0x44 -> reply rtc[0], state=RTC_READ (stream 42)
        cmd==0x57 -> reply 0x30,  state=RTC_WRITE (absorb 24)
        cmd==0x52 -> reply 0x44 (re-handshake)
        else      -> reply 0x00
RTC_READ:  reply rtc[i++]; if i>=42 state=ACTIVE
RTC_WRITE: discard incoming byte; i++; if i>=24 state=ACTIVE; reply 0x00
```

---

## 3. Scan-code table (LOCKED: GBE+ convention)

Single byte per key. Hex → meaning in **CAPS mode / NUM mode**. `0x00` = no key.

| Code | CAPS / NUM | Code | CAPS / NUM | Code | CAPS / NUM |
|---|---|---|---|---|---|
| `0x01` | App 1 — Clock        | `0x18` | I / !   | `0x29` | X / 8 |
| `0x02` | App 2 — Temp Conv    | `0x19` | O / £   | `0x2A` | C / 9 |
| `0x03` | App 3 — Currency     | `0x1A` | P / *   | `0x2B` | V / . |
| `0x04` | App 4 — Calculator   | `0x1B` | $ / #   | `0x2C` | B / % |
| `0x05` | App 5 — Calendar     | `0x1C` | A / 4   | `0x2D` | N / = |
| `0x06` | App 6 — Unit Conv    | `0x1D` | S / 5   | `0x2E` | M / C |
| `0x07` | App 7 — Database     | `0x1E` | D / 6   | `0x2F` | , / < |
| `0x08` | App 8 — Translator   | `0x1F` | F / +   | `0x30` | . / > |
| `0x09` | App 9 — Phone dialer | `0x20` | G / -   | `0x31` | / / ? |
| `0x0A` | Escape               | `0x21` | H / ×   | `0x32` | **CAPS toggle** |
| `0x0B` | Delete / Backspace   | `0x22` | J / ÷   | `0x33` | " / 0 |
| `0x0C` | Insert               | `0x23` | K / (   | `0x34` | Space |
| `0x10` | ← Left arrow         | `0x24` | L / )   | `0x35` | ' / @ |
| `0x11` | Q / 1                | `0x25` | ; / :   | `0x36` | ↑ Up arrow |
| `0x12` | W / 2                | `0x26` | Return / Enter | `0x37` | ↓ Down arrow |
| `0x13` | E / 3                | `0x27` | **NUM toggle** | `0x38` | → Right arrow |
| `0x14` | R / M+               | `0x28` | Z / 7   |  |  |
| `0x15` | T / M-               |  |  |  |  |
| `0x16` | Y / MR               |  |  |  |  |
| `0x17` | U / MC               |  |  |  |  |

**Modifier model (LOCKED): mode TOGGLES, no held shift.**
`0x32` (CAPS) and `0x27` (NUM) are toggle keys. The firmware just emits the raw
scan code from the table when those physical keys are pressed; the ROM tracks the
mode and reinterprets the other codes. Do **not** pre-resolve in firmware.

That makes **53 distinct scan codes that map to physical keys** (9 app + Esc/Del/Ins
+ 4 arrows + 30 letter keys + `$`/`"`/`'` + Return + Space + CAPS + NUM). Lay the
matrix out to *these codes*, not to a guessed physical layout.

---

## 4. RTC payload (read = 0x44)

42-byte stream. **Every field is ASCII digit characters, and the whole buffer
must be filled with `'0'` (0x30) — a `0x00` byte anywhere signals an error to the
ROM.** (Verified against GBE+ `workboy_get_time`, the implementation confirmed to
run the real ROM; corroborated by SameBoy, which sends ASCII hex of a BCD buffer.)

| Offset | Field | Encoding |
|---|---|---|
| `0x04`,`0x05` | seconds | two ASCII digits, e.g. 37 s → `'3'`,`'7'` |
| `0x06`,`0x07` | minutes | two ASCII digits |
| `0x08`,`0x09` | hours | two ASCII digits |
| `0x0A`,`0x0B` | day | two ASCII digits |
| `0x0C`,`0x0D` | month | two ASCII digits (1–12) |
| `0x1E`,`0x1F` | year | `[0x1E] = 0x30 + (Y / 16)`, `[0x1F] = 0x30 + (Y % 16)`, where `Y = year − 1900` |
| all others | undocumented | leave as `'0'` (0x30) — **never `0x00`** |

Write (`0x57`): reply `0x30`, then absorb the GB's stream. GBE+ loops `index < 24`;
Dan Docs prose says 23. **Resolve by definition: absorb 24 slots, re-sync on the
next `0x52`/idle gap, never hard-fail on an exact count.** GBE+ ignores the written
data; our firmware may parse it to set the clock or ignore it.

---

## 5. Disputed details (decide once, `#define` so they can flip)

| Detail | GBE+ (LOCKED) | SameBoy (alt) |
|---|---|---|
| No-key value | `0x00` | `0xFF` (`GB_WORKBOY_NONE`) |
| Modifiers | CAPS/NUM **toggles** | held-shift: `REQUIRE_SHIFT 0x40` / `FORBID_SHIFT 0x80`, with `SHIFT_DOWN 39` / `SHIFT_UP 50` control bytes that can span **two** polls |
| RTC write length | 24-slot loop | — |

Keep `WORKBOY_NOKEY`, the modifier model, and the RTC-write count behind
`#define`s. If a real-hardware capture (Layer 3 in the bring-up plan) shows the
ROM rejecting input, flip to the SameBoy convention and retest.
