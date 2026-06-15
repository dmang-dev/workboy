/*
 * calc.c — integer 4-function calculator (App-4 / scancode 0x04).
 * Digits come from the NUM-layer keys; operators from the +,-,*,/ keys.
 */
#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdio.h>
#include "calc.h"
#include "ui.h"
#include "workboy_link.h"
#include "scancodes.h"

/* NUM-layer digit for a scan code, or -1. (Q..=1.. row, A..=4.. row, Z..=7.. row, "=0) */
static int8_t digit_of(uint8_t code) {
    switch (code) {
        case 0x11: return 1; case 0x12: return 2; case 0x13: return 3;
        case 0x1C: return 4; case 0x1D: return 5; case 0x1E: return 6;
        case 0x28: return 7; case 0x29: return 8; case 0x2A: return 9;
        case 0x33: return 0;
        default:   return -1;
    }
}

static long apply(long a, char op, long b) {
    switch (op) {
        case '+': return a + b;
        case '-': return a - b;
        case '*': return a * b;
        case '/': return b ? a / b : 0;
    }
    return b;
}

static void show(long v, char op) {
    gotoxy(0, 4); put_long(v); printf("          ");
    gotoxy(0, 6); printf("op: %c", op ? op : ' ');
}

void calc_screen(void) {
    long acc = 0, cur = 0;
    char op = 0;
    uint8_t have = 0, code;
    int8_t d;

    clrscr();
    gotoxy(0, 0);  printf("CALCULATOR");
    gotoxy(0, 16); printf("NUM 0-9 F+ G- H*");
    gotoxy(0, 17); printf("J/ N== Mclr Esc");
    show(0, 0);

    for (;;) {
        wait_vbl_done();
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;

        d = digit_of(code);
        if (d >= 0) { cur = cur * 10 + d; have = 1; show(cur, op); continue; }

        switch (code) {
            case WB_KEY_ESC:                         /* exit            */
                clrscr(); return;
            case 0x2E:                               /* M/C key = clear */
                acc = cur = 0; op = 0; have = 0; show(0, 0); break;
            case 0x1F: case 0x20: case 0x21: case 0x22:   /* + - * /     */
                acc = op ? apply(acc, op, have ? cur : acc) : (have ? cur : acc);
                op  = (code == 0x1F) ? '+' : (code == 0x20) ? '-' :
                      (code == 0x21) ? '*' : '/';
                cur = 0; have = 0; show(acc, op); break;
            case 0x26: case 0x2D:                    /* Enter or =       */
                if (op) { acc = apply(acc, op, have ? cur : acc); op = 0; }
                else if (have) acc = cur;
                cur = 0; have = 0; show(acc, 0); break;
        }
    }
}
