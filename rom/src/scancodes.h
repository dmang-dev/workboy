/*
 * scancodes.h — WorkBoy scan-code -> ASCII mapping (shared contract).
 * Must stay identical to firmware/workboy_keyboard.c SCANCODE[][] and
 * WORKBOY_PROTOCOL.md. GBE+ convention: CAPS/NUM are mode toggles.
 */
#ifndef SCANCODES_H
#define SCANCODES_H

#include <stdint.h>

/* App-launch keys */
#define WB_KEY_CLOCK     0x01
#define WB_KEY_TEMP      0x02
#define WB_KEY_CURRENCY  0x03
#define WB_KEY_CALC      0x04
#define WB_KEY_CALENDAR  0x05
#define WB_KEY_UNITS     0x06
#define WB_KEY_DATABASE  0x07
#define WB_KEY_TRANSLATE 0x08
#define WB_KEY_PHONE     0x09
/* Editing / control */
#define WB_KEY_ESC       0x0A
#define WB_KEY_BACKSPACE 0x0B
#define WB_KEY_INSERT    0x0C
#define WB_KEY_LEFT      0x10
#define WB_KEY_ENTER     0x26
#define WB_KEY_NUM       0x27
#define WB_KEY_CAPS      0x32
#define WB_KEY_SPACE     0x34
#define WB_KEY_UP        0x36
#define WB_KEY_DOWN      0x37
#define WB_KEY_RIGHT     0x38

/* Highest scan code in the table. */
#define WB_SCAN_MAX      0x38

/* Returns a printable ASCII char for `code` in the given mode, or 0 if the
 * key is non-printable (app keys, arrows, toggles, calc-memory keys, etc.). */
char wb_scancode_to_ascii(uint8_t code, uint8_t num_mode);

#endif /* SCANCODES_H */
