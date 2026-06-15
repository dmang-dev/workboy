#!/usr/bin/env python3
"""
keymap.py — SINGLE SOURCE OF TRUTH for the WorkBoy keyboard layout.

53 keys in reading order. The reading-order index i maps to the electrical
matrix cell (i // COLS, i % COLS) on the 8x7 diode matrix, so matrix rows are
runs of physically-adjacent keys (clean PCB routing). Scan codes are fixed by
the protocol (WORKBOY_PROTOCOL.md); physical x/y/width are our design choice,
shaped like the original ~146 x 89 mm WorkBoy.

Consumed by: firmware (scancode_map.h), the KiCad netlist generator,
tests/protocol_sim.py, and the case scripts. Edit HERE, then run
layout/gen_layout.py and tests/run_ci.py.
"""

ROWS, COLS = 8, 7
LAYOUT_COLS, LAYOUT_ROWS = 12, 5     # max width / height in key units


def K(label, code, x, y, w=1.0):
    return dict(label=label, code=code, x=x, y=y, w=w)


KEYS = [
    # Row 0 — app / function row (12)
    K("Clk", 0x01, 0, 0), K("Tmp", 0x02, 1, 0), K("Cur", 0x03, 2, 0), K("Clc", 0x04, 3, 0),
    K("Dte", 0x05, 4, 0), K("Cnv", 0x06, 5, 0), K("DB",  0x07, 6, 0), K("Trn", 0x08, 7, 0),
    K("Tel", 0x09, 8, 0), K("Esc", 0x0A, 9, 0), K("Bsp", 0x0B, 10, 0), K("Ins", 0x0C, 11, 0),
    # Row 1 — QWERTY top (11)
    K("Q", 0x11, 0, 1), K("W", 0x12, 1, 1), K("E", 0x13, 2, 1), K("R", 0x14, 3, 1), K("T", 0x15, 4, 1),
    K("Y", 0x16, 5, 1), K("U", 0x17, 6, 1), K("I", 0x18, 7, 1), K("O", 0x19, 8, 1), K("P", 0x1A, 9, 1),
    K("$", 0x1B, 10, 1),
    # Row 2 — home (11)
    K("A", 0x1C, 0, 2), K("S", 0x1D, 1, 2), K("D", 0x1E, 2, 2), K("F", 0x1F, 3, 2), K("G", 0x20, 4, 2),
    K("H", 0x21, 5, 2), K("J", 0x22, 6, 2), K("K", 0x23, 7, 2), K("L", 0x24, 8, 2), K(";", 0x25, 9, 2),
    K("Ent", 0x26, 10, 2),
    # Row 3 — bottom letters (11)
    K("NUM", 0x27, 0, 3), K("Z", 0x28, 1, 3), K("X", 0x29, 2, 3), K("C", 0x2A, 3, 3), K("V", 0x2B, 4, 3),
    K("B", 0x2C, 5, 3), K("N", 0x2D, 6, 3), K("M", 0x2E, 7, 3), K(",", 0x2F, 8, 3), K(".", 0x30, 9, 3),
    K("/", 0x31, 10, 3),
    # Row 4 — space + arrows (8); Space is 5u wide
    K("CAP", 0x32, 0, 4), K('"', 0x33, 1, 4), K("Space", 0x34, 2, 4, 5.0), K("'", 0x35, 7, 4),
    K("Lt", 0x10, 8, 4), K("Up", 0x36, 9, 4), K("Dn", 0x37, 10, 4), K("Rt", 0x38, 11, 4),
]
assert len(KEYS) == 53, f"expected 53 keys, got {len(KEYS)}"


def matrix_rc(i):
    """Reading-order index -> (matrix_row, matrix_col)."""
    return (i // COLS, i % COLS)


def scancode_grid():
    """8x7 grid of scan codes (0x00 = unpopulated cell)."""
    g = [[0x00] * COLS for _ in range(ROWS)]
    for i, k in enumerate(KEYS):
        r, c = matrix_rc(i)
        g[r][c] = k["code"]
    return g


def designator(i):
    """Switch/diode reference for the key at reading-order index i."""
    return i + 1                      # SW1..SW53 / D1..D53 (matches the netlist)


def centers(pitch):
    """Key centres in mm, origin-centred, row 0 at +y (CAD up). -> (cx, cy, w_units)."""
    total_w = LAYOUT_COLS * pitch
    total_h = LAYOUT_ROWS * pitch
    out = []
    for k in KEYS:
        cx = (k["x"] + k["w"] / 2.0) * pitch - total_w / 2.0
        cy = total_h / 2.0 - (k["y"] + 0.5) * pitch
        out.append((cx, cy, k["w"]))
    return out


if __name__ == "__main__":
    g = scancode_grid()
    print("8x7 scan-code matrix (reading-order fill):")
    for r in range(ROWS):
        print("  " + " ".join(f"{g[r][c]:02X}" for c in range(COLS)))
    print(f"{len(KEYS)} keys, {sum(1 for row in g for c in row if c)} populated cells")
