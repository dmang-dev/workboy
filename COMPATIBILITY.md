# Console compatibility

Which Game Boy hardware the recreated WorkBoy works on, and why.

> **Short version:** the WorkBoy is a **5 V** peripheral on the **8-bit link
> protocol**. Every Nintendo handheld that can run a Game Boy / Game Boy Color
> *cartridge* drives its link port at **5 V in 8-bit mode** — including the GBA
> and GBA SP. So **one 5 V design covers the whole family**. The only variable
> is which cable plug you harvest.

## The table

| System | Runs GB/GBC carts? | Link connector | Link level in 8-bit mode | WorkBoy works? |
|---|---|---|---|---|
| **DMG-01** Game Boy | ✅ | DMG "large" 6-pin | **5 V** | ✅ **design target** |
| **MGB-001** Game Boy Pocket | ✅ | MGB/CGB "small" 6-pin | **5 V** | ✅ small-plug cable |
| **MGB-101** Game Boy Light | ✅ | small 6-pin | **5 V** | ✅ small-plug cable |
| **CGB-001** Game Boy Color | ✅ | small 6-pin | **5 V** | ✅ small-plug cable |
| **AGB-001** Game Boy Advance | ✅ (8-bit mode) | GBA 6-pin | **5 V** when an 8-bit cart is inserted | ⚠️ likely — **needs bench proof**, see below |
| **AGS-001 / AGS-101** GBA SP | ✅ (8-bit mode) | GBA 6-pin | **5 V** in 8-bit mode | ⚠️ likely — needs bench proof |
| **DOL-017** Game Boy Player | ✅ (8-bit mode) | GBA-style | presumed 5 V in 8-bit mode | ⚠️ untested |
| **OXY-001** Game Boy Micro | ❌ **GBA-only** | proprietary | 3.3 V, GBA protocol only | ❌ **impossible** — cannot run GB/GBC software at all |
| **SGB / SGB2** Super Game Boy | ✅ (via SNES) | **none** | — | ❌ **impossible** — the cartridge has no link port |

### Why the GBA still works

The GBA's link port is **mode-switched by the inserted cartridge**. With a GBA
cartridge it runs the 32-bit protocol at 3.3 V; drop in an 8-bit (GB/GBC)
cartridge and the console falls back to the Game Boy serial protocol **at 5 V**.
That is also why an 8-bit link cable is required in that mode — GBA link cables
will not work for 8-bit linking.

**Consequence for this project:** no level shifter, no second board revision,
and no separate "GBC version" or "GBA version" of the firmware. The protocol
and the electrical levels are the same everywhere the cartridge runs.

> ⚠️ **This is documented behaviour, not yet verified on a bench by this
> project.** Before trusting it, measure pin 1 (VCC) and an idle SC/SO line on
> your own GBA with the WorkBoy cartridge inserted and confirm ~5 V. Report back
> and this table can be upgraded from "likely" to "verified".

### The two impossible cases

- **Game Boy Micro** does not have Game Boy / Game Boy Color backward
  compatibility at all — it is a GBA-only machine. No cable or adapter fixes
  this; the console cannot execute the cartridge.
- **Super Game Boy** is a *cartridge* for the SNES. It has no link port, so
  there is nowhere to attach a WorkBoy.

## Cables — the only thing that actually varies

The board is the same in every case. What changes is the plug on the other end,
and there is **no modern catalogue part** for any of these connectors, so the
build harvests one from a real cable (see `BUILD_PLAN.md`).

| Target | Cable to harvest |
|---|---|
| DMG-01 | DMG-04 link cable (large plug) — or MGB-004 / DMG-14 adapter |
| Pocket / Light / Color | MGB-008 or CGB-003 (small plug) |
| GBA / GBA SP in 8-bit mode | an **8-bit** small-plug cable, *not* an AGB-005 GBA cable |

A universal build is possible: fit the small (MGB/CGB) plug and keep a **DMG-14
adapter** in the box, which covers the large-connector DMG from the same board.

## If you ever do want native GBA-mode support

That is a genuinely different project, not a variant of this one — different
protocol (GBA SIO: normal/multiplayer/UART modes), different levels (3.3 V),
different cartridge software. `BUILD_PLAN.md` §3.1 already documents what the
3.3 V electrical variant would need (**TXS0108E** level shifter + **AMS1117-3.3**
or **ME6211** regulator) should anyone want to explore it.

## Should this be split into separate repos?

**No.** One repo, one board, one firmware, one ROM.

A split would fork ~90% shared content — the keyboard matrix, the scan-code
table, the protocol driver, the case, the CI — to express a difference that
does not exist electrically. The GB, GBC and GBA-in-8-bit-mode cases are the
*same* 5 V peripheral speaking the *same* protocol; only the cable plug differs,
and that is a mechanical choice made at assembly time, not a board revision.

If a true 3.3 V native-GBA design ever happens, the right structure is a
**hardware variant directory** in this repo (`kicad/rev-b-3v3/`) sharing the
layout and firmware, or a separate project if the cartridge software diverges
entirely.
