#!/usr/bin/env python3
"""
protocol_sim.py — runnable cross-check of the WorkBoy firmware <-> ROM protocol.

Mirrors the corrected firmware SPI-slave state machine (firmware/workboy_keyboard.c)
and the ROM master driver (rom/src/workboy_link.c), exchanges bytes through the
exact one-transfer pipeline, and asserts the results match what the real ROM
expects (per GBE+ workboy_process / workboy_get_time). Pure stdlib; run: python protocol_sim.py
"""

ST_IDLE, ST_ACTIVE, ST_RTC_RD, ST_RTC_WR = range(4)
RTC_LEN = 42

# Firmware SCANCODE[ROWS][COLS] from the single source of truth (layout/keymap.py)
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "layout"))
import keymap as _km
SCAN = _km.scancode_grid()


class Slave:
    """Mirror of the ATmega SPI_STC ISR + format_rtc."""
    def __init__(self):
        self.state = ST_IDLE
        self.reported_key = 0
        self.key_consumed = 1
        self.idx = 0
        self.rtc = [ord('0')] * RTC_LEN     # static init fill (0x30)
        self.wr = [0] * 24                  # RTC-write payload buffer
        self.staged = 0x00                  # SPDR preload = WB_NOKEY

    def set_key(self, code):
        self.reported_key = code
        self.key_consumed = 0

    def decode_write(self):
        b = self.wr
        bcd = lambda x: (x >> 4) * 10 + (x & 0xF)
        return dict(hr=bcd(b[10]), mi=bcd(b[9]), se=bcd(b[8]),
                    day=bcd(b[11] & 0x3F), mon=bcd(b[12] & 0x1F), yr=1900 + b[21])

    def format_rtc(self, sec, minu, hr, day, mon, yr):
        tmp = [ord('0')] * RTC_LEN
        def put2(p, v): tmp[p] = ord('0') + (v // 10) % 10; tmp[p+1] = ord('0') + v % 10
        put2(0x04, sec); put2(0x06, minu); put2(0x08, hr)
        put2(0x0A, day); put2(0x0C, mon)
        years = (yr - 1900) & 0xFF
        tmp[0x1E] = 0x30 + (years // 16)
        tmp[0x1F] = 0x30 + (years % 16)
        if self.state != ST_RTC_RD:
            self.rtc = tmp

    def _process(self, cmd):
        out = 0x00
        if self.state == ST_IDLE:
            if cmd == 0x52:
                out = 0x44; self.state = ST_ACTIVE
        elif self.state == ST_ACTIVE:
            if cmd == 0x4F:
                out = 0 if self.key_consumed else self.reported_key
                self.key_consumed = 1
            elif cmd == 0x44:
                self.idx = 0; self.state = ST_RTC_RD
                out = self.rtc[self.idx]; self.idx += 1
            elif cmd == 0x57:
                self.idx = 0; self.state = ST_RTC_WR; out = 0x30
            elif cmd == 0x52:
                out = 0x44
        elif self.state == ST_RTC_RD:
            out = self.rtc[self.idx]; self.idx += 1
            if self.idx >= RTC_LEN: self.state = ST_ACTIVE
        elif self.state == ST_RTC_WR:
            if self.idx < 24: self.wr[self.idx] = cmd
            self.idx += 1
            if self.idx >= 24: self.state = ST_ACTIVE
        return out

    def transfer(self, b_gb):
        """GB reads the previously-staged byte; slave then stages the next."""
        out = self.staged
        self.staged = self._process(b_gb)
        return out


# --- ROM master driver (mirror of workboy_link.c) ---
def wb_xfer(s, b): return s.transfer(b)

def wb_init(s):
    for _ in range(16):
        wb_xfer(s, 0x52)                       # stage reply
        if wb_xfer(s, 0x00) == 0x44: return 1  # read on next transfer
    return 0

def wb_poll_key(s):
    wb_xfer(s, 0x4F)
    return wb_xfer(s, 0x4F)

def wb_read_rtc(s):
    wb_xfer(s, 0x44)
    return [wb_xfer(s, 0x00) for _ in range(RTC_LEN)]


def main():
    ok = 0; fail = 0
    def check(name, cond):
        nonlocal ok, fail
        print(("  PASS " if cond else "  FAIL ") + name); ok += cond; fail += not cond

    print("1) scan-code matrix completeness")
    flat = [c for row in SCAN for c in row if c != 0x00]
    expected = set(range(0x01, 0x0D)) | set(range(0x10, 0x39))   # 12 + 41 = 53
    check("exactly 53 keys", len(flat) == 53)
    check("no duplicate scan codes", len(flat) == len(set(flat)))
    check("matrix set == GBE+ doc set", set(flat) == expected)

    print("2) init handshake")
    s = Slave()
    check("wb_init() returns 1 (0x52 -> 0x44)", wb_init(s) == 1)
    check("state is ACTIVE after init", s.state == ST_ACTIVE)

    print("3) keyboard poll")
    s.set_key(0x11)                            # 'Q'
    k = wb_poll_key(s)
    check("poll returns the pressed key 0x11", k == 0x11)
    check("repeat suppressed (next poll = 0x00)", wb_poll_key(s) == 0x00)

    print("4) RTC read (13:37:45, 2026-06-14)")
    s.format_rtc(45, 37, 13, 14, 6, 2026)
    buf = wb_read_rtc(s)
    check("frame is 42 bytes", len(buf) == RTC_LEN)
    check("NO zero bytes (0x00 = error to ROM)", all(b != 0 for b in buf))
    hhmmss = "".join(chr(b) for b in (buf[8],buf[9],buf[6],buf[7],buf[4],buf[5]))
    check(f"hh:mm:ss decodes to 13:37:45 (got {hhmmss})", hhmmss == "133745")
    check("day decodes to 14", chr(buf[0x0A])+chr(buf[0x0B]) == "14")
    check("month decodes to 06", chr(buf[0x0C])+chr(buf[0x0D]) == "06")
    # year 2026 -> years=126 -> 0x30+7='7', 0x30+14=0x3E (GBE+ formula)
    check("year bytes per GBE+ formula (0x37,0x3E)", buf[0x1E]==0x37 and buf[0x1F]==0x3E)

    print("5) RTC write sets the clock (12:34:56, 2026)")
    buf = [0] * 24
    buf[6] = 0x04
    buf[10] = (1 << 4) | 2      # 12 hours BCD
    buf[9]  = (3 << 4) | 4      # 34 minutes BCD
    buf[8]  = (5 << 4) | 6      # 56 seconds BCD
    buf[21] = 126               # years since 1900 -> 2026
    wb_xfer(s, 0x57)
    for b in buf: wb_xfer(s, b)
    check("state ACTIVE after 24-byte write", s.state == ST_ACTIVE)
    w = s.decode_write()
    check(f"write decodes to 12:34:56 (got {w['hr']:02d}:{w['mi']:02d}:{w['se']:02d})",
          (w['hr'], w['mi'], w['se']) == (12, 34, 56))
    check("write year decodes to 2026", w['yr'] == 2026)

    print(f"\n{ok} passed, {fail} failed")
    raise SystemExit(1 if fail else 0)


if __name__ == "__main__":
    main()
