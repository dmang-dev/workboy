/*
 * main.c — WorkBoy homebrew (clean-room) — bring-up demo.
 *
 * Proves the recreated keyboard works end-to-end: runs the link handshake,
 * echoes typed characters (a notepad), toggles NUM mode, and prints a
 * timestamp from the keyboard's RTC when the Clock app-key is pressed.
 *
 * This is a foundation, not the full 12-app suite. It deliberately contains
 * NO leaked Nintendo code or assets — only the documented wire protocol.
 *
 * Build: GBDK-2020 (see ../Makefile). Cartridge type MBC1+RAM+BATTERY.
 */
#include <gb/gb.h>
#include <stdio.h>
#include "workboy_link.h"
#include "scancodes.h"
#include "phonebook.h"
#include "calc.h"
#include "clock.h"

void main(void) {
    uint8_t num_mode = 0;
    uint8_t code;

    DISPLAY_ON;
    printf("WorkBoy homebrew\nclean-room demo\n\n");

    if (wb_init()) {
        printf("Keyboard: OK\nApps: Clk Clc DB\nEsc=back. Type:\n\n");
    } else {
        printf("Keyboard: NONE\nCheck link cable\n& power, reset.\n\n");
    }

    for (;;) {
        wait_vbl_done();
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;

        switch (code) {
            case WB_KEY_NUM:      num_mode ^= 1;         break;
            case WB_KEY_CAPS:     num_mode = 0;          break; /* demo: CAPS = letters */
            case WB_KEY_ENTER:    printf("\n");          break;
            case WB_KEY_SPACE:    printf(" ");           break;
            case WB_KEY_CLOCK:    clock_screen(); printf("-- notepad --\n"); break;
            case WB_KEY_CALC:     calc_screen();  printf("-- notepad --\n"); break;
            case WB_KEY_DATABASE: pb_screen();    printf("-- notepad --\n"); break;
            default: {
                char ch = wb_scancode_to_ascii(code, num_mode);
                if (ch) putchar(ch);
                break;
            }
        }
    }
}
