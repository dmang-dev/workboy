/* scancodes.c — see scancodes.h. Tables follow WORKBOY_PROTOCOL.md exactly. */
#include "scancodes.h"

/* CAPS-mode characters (letters + base symbols). 0 = non-printable. */
static const char caps[WB_SCAN_MAX + 1] = {
    [0x11] = 'Q', [0x12] = 'W', [0x13] = 'E', [0x14] = 'R', [0x15] = 'T',
    [0x16] = 'Y', [0x17] = 'U', [0x18] = 'I', [0x19] = 'O', [0x1A] = 'P',
    [0x1B] = '$',
    [0x1C] = 'A', [0x1D] = 'S', [0x1E] = 'D', [0x1F] = 'F', [0x20] = 'G',
    [0x21] = 'H', [0x22] = 'J', [0x23] = 'K', [0x24] = 'L', [0x25] = ';',
    [0x28] = 'Z', [0x29] = 'X', [0x2A] = 'C', [0x2B] = 'V', [0x2C] = 'B',
    [0x2D] = 'N', [0x2E] = 'M', [0x2F] = ',', [0x30] = '.', [0x31] = '/',
    [0x33] = '"', [0x34] = ' ', [0x35] = '\'',
};

/* NUM-mode characters (digits + symbols). Calc-memory/non-ASCII keys = 0. */
static const char num[WB_SCAN_MAX + 1] = {
    [0x11] = '1', [0x12] = '2', [0x13] = '3',
    [0x18] = '!', [0x1A] = '*', [0x1B] = '#',
    [0x1C] = '4', [0x1D] = '5', [0x1E] = '6', [0x1F] = '+', [0x20] = '-',
    [0x23] = '(', [0x24] = ')', [0x25] = ':',
    [0x28] = '7', [0x29] = '8', [0x2A] = '9', [0x2B] = '.', [0x2C] = '%',
    [0x2D] = '=', [0x2F] = '<', [0x30] = '>', [0x31] = '?',
    [0x33] = '0', [0x34] = ' ', [0x35] = '@',
};

char wb_scancode_to_ascii(uint8_t code, uint8_t num_mode) {
    if (code > WB_SCAN_MAX) return 0;
    return num_mode ? num[code] : caps[code];
}
