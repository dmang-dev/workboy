# WorkBoy homebrew ROM (clean-room)

A **legally distributable** Game Boy cartridge that drives the recreated WorkBoy
keyboard over the link port. Built only from the documented wire protocol
([`../WORKBOY_PROTOCOL.md`](../WORKBOY_PROTOCOL.md)) — it contains **no leaked
Nintendo code or assets**.

> This is a **bring-up demo / foundation**, not the full 12-app suite. It proves
> the keyboard works end-to-end: link handshake, a notepad that echoes typed
> characters, NUM-mode toggling, and an RTC timestamp from the keyboard's clock.
> Extend it app-by-app from here.

## Files
| File | Role |
|---|---|
| `src/workboy_link.c/.h` | GB **master**-side link driver (the 4 commands) |
| `src/scancodes.c/.h` | scan-code → ASCII map (kept identical to the firmware) |
| `src/phonebook.c/.h` | **phone book stored in the 32 KB battery SRAM** (add / list / scroll) |
| `src/main.c` | home: notepad + clock + `App-7` opens the phone book |
| `Makefile` | GBDK-2020 build → `workboy_homebrew.gb` (MBC1+RAM+BATTERY) |

> **Builds clean** with GBDK-2020 → a 128 KB MBC1+RAM+BATTERY image (verified
> header: cart `0x03`, 128 KB ROM, 32 KB SRAM). The phone book uses MBC1
> RAM-banking mode across all four 8 KB banks (128-byte records, up to 255
> entries) and persists on a battery-backed cart.

## Build
1. Install **GBDK-2020** (<https://github.com/gbdk-2020/gbdk-2020/releases>).
2. Build, pointing at your install:
   ```sh
   make GBDK_HOME=/opt/gbdk          # Linux/macOS
   make GBDK_HOME=C:/gbdk            # Windows (forward slashes)
   ```
3. Output: `workboy_homebrew.gb`.

## Run
- **EverDrive GB / EZ-Flash Jr.:** copy `workboy_homebrew.gb` to the microSD and
  pick it from the menu. Saves use the cart's battery SRAM.
- **Repro cart:** flash to an **MBC1 + RAM + BATTERY** cartridge (the Makefile sets
  cart type `0x03`, 32 KB SRAM). A no-mapper 32 KB cart will **not** work.
- Connect the recreated keyboard to the link port, power it (USB-C/battery), and
  reset. You should see `Keyboard: OK`, then typing echoes on screen; press the
  Clock app-key to print the time.

## Protocol notes baked in
- GB is the **master** (internal clock, `SC_REG = 0x81`). Responses are pipelined
  by one transfer — `wb_poll_key()` polls twice and returns the second byte.
- Commands: `0x52` Init→`0x44`, `0x4F` Poll→scancode, `0x44` Read-RTC→42 bytes,
  `0x57` Write-RTC (not used by this demo).
- `wb_xfer()` has a spin-guard so a missing/unpowered keyboard can't hang the ROM.

## Validate on a logic analyzer first
If the handshake fails on real hardware, check the SPI edge convention against the
keyboard firmware (Mode 1 vs Mode 3) and confirm the keyboard's no-key value is
`0x00` (GBE+) — both are `#define`-switchable on the firmware side.

## Extending toward the full suite
Add apps as screens driven by the app-launch scancodes (`0x01`–`0x09`). Persist
data in the 32 KB battery SRAM (`ENABLE_RAM`, write to `0xA000`+ banks). Re-create
the calculator / phone book / calendar logic from scratch — do **not** copy the
leaked ROM's code or data.
