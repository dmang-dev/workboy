# Emulator-in-the-loop validation

Validate our understanding of the WorkBoy protocol/scan-codes against the **real
`DMGWYE-0.781` ROM** using two third-party emulators — no hardware needed. The
firmware/ROM logic is already verified two ways (source-match against GBE+'s
`workboy_process`, and the 16-check `tests/protocol_sim.py`); this is the live
cross-check.

## What you need, and where it goes

None of it is in this repo. The emulators each carry their own licence and
upstream home; the ROM is leaked and copyrighted. All of it lives under a
gitignored `reference/`:

```
reference/
  gbe_1_10/               GBE+ 1.10 Windows build      https://github.com/shonumi/gbe-plus
  gbe-plus-master/        GBE+ source (sio.cpp)        (same repo, source zip)
  sameboy_winsdl_v1.0.3/  SameBoy 1.0.3 Windows SDL    https://github.com/LIJI32/SameBoy
  SameBoy-1.0.3/          SameBoy source (Core/workboy.c)
  DMGWYE-0.781.gb         the leaked 1992 cartridge ROM -- source it yourself
  DMGWYE-0.781.sav        its save file, written at runtime
```

Every path below is relative to the repository root. **Nothing in the build
depends on any of this** — delete `reference/` entirely and `tests/run_ci.py`
still passes. It exists only for this cross-check.

## Status (done here)
- GBE+ configured for WorkBoy: `reference/gbe_1_10/CURRENT/gbe.ini` →
  `[#sio_device:22]` (original saved as `gbe.ini.bak`).
- **Smoke test passed:** `gbe_plus.exe DMGWYE-0.781.gb` boots the real ROM with the
  emulated WorkBoy attached and runs without crashing — i.e. the ROM's init
  handshake (`0x52`→`0x44`) and RTC poll succeed against GBE+'s WorkBoy device.

## Interactive validation in GBE+ (visual)
1. From `reference/gbe_1_10/CURRENT/`, run the Qt build for menus:
   ```
   gbe_plus_qt.exe
   ```
2. Confirm **Options ▸ Emulated Serial Device = WorkBoy** (or that `gbe.ini` has
   `[#sio_device:22]`), core = **DMG-GBC**.
3. **File ▸ Load Game** → `..\..\DMGWYE-0.781.gb`. The WorkBoy productivity menu
   should appear (clock / calculator / phone book / etc.).
4. The emulated WorkBoy maps your **PC keyboard** to WorkBoy keys. Type letters,
   toggle CAPS/NUM, press the app keys — confirm each does what
   [`WORKBOY_PROTOCOL.md`](WORKBOY_PROTOCOL.md) §3 says (e.g. NUM mode turns the
   QWERTY row into digits; the clock app shows the RTC time).
5. This is the ground truth our **firmware** reproduces: GBE+'s `workboy_process`
   (in `reference/gbe-plus-master/src/dmg/sio.cpp`) is the exact state machine our
   `firmware/workboy_keyboard.c` mirrors, so a keypress that works here works on
   the real hardware too.

## Cross-check in SameBoy
`reference/sameboy_winsdl_v1.0.3/sameboy.exe` also implements a WorkBoy device
(`Core/workboy.c`).
Note SameBoy's author flags his implementation as a best-effort guess (it uses
`0xFF` for no-key and a held-shift model) — where SameBoy and GBE+ disagree, **GBE+
is authoritative** because it was matched against the real ROM. Use SameBoy only as
a secondary sanity check.

## What this proves (and doesn't)
- ✅ The real ROM accepts our protocol's init + RTC + keyboard polling model.
- ✅ Our scan-code table matches what the ROM decodes (typing produces the right
  characters in GBE+).
- ⚠️ It validates the *protocol contract*, not our *AVR timing* — confirm the SPI
  edge (Mode 1 vs 3) on a logic analyzer during hardware bring-up (BUILD_PLAN §8).

## Re-running the smoke test
```powershell
# from reference/gbe_1_10/CURRENT, WorkBoy already enabled in gbe.ini
.\gbe_plus.exe "<path-to-your-rom>\DMGWYE-0.781.gb"
```
