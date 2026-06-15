/*
 * phonebook.c — battery-backed phone book in the cart's 32 KB SRAM.
 * See phonebook.h. Uses MBC1 in RAM-banking mode (4 x 8 KB banks).
 *
 * SRAM is treated as a flat array of 128-byte records (64 per 8 KB bank, so a
 * record never crosses a bank boundary). Record 0 is the header; entries are
 * records 1..count. With MBC1+RAM+BATTERY this persists across power cycles.
 */
#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdio.h>
#include "phonebook.h"
#include "workboy_link.h"
#include "scancodes.h"

/* MBC1 control registers — writes in 0x0000-0x7FFF are caught by the mapper. */
#define MBC_RAMG (*(volatile uint8_t *)0x0000)   /* 0x0A enables SRAM        */
#define MBC_RAMB (*(volatile uint8_t *)0x4000)   /* RAM bank 0-3 (mode 1)    */
#define MBC_MODE (*(volatile uint8_t *)0x6000)   /* 1 = RAM-banking mode     */
#define SRAM     ((volatile uint8_t *)0xA000)    /* 8 KB SRAM window         */

/* Select the bank holding record r and return a pointer to its 128 bytes. */
static volatile uint8_t *rec_ptr(uint8_t r) {
    MBC_RAMB = (uint8_t)(r >> 6);                 /* 64 records per bank */
    return SRAM + ((uint16_t)(r & 63) << 7);
}

void pb_init(void) {
    MBC_RAMG = 0x0A;                              /* enable SRAM           */
    MBC_MODE = 1;                                 /* 32 KB RAM-banking mode */
    MBC_RAMB = 0;
    if (SRAM[1] != 'W' || SRAM[2] != 'B') {       /* fresh / corrupt header */
        SRAM[0] = 0; SRAM[1] = 'W'; SRAM[2] = 'B';
    }
}

uint8_t pb_count(void) {
    MBC_RAMB = 0;
    return SRAM[0];
}

static void set_count(uint8_t n) {
    MBC_RAMB = 0;
    SRAM[0] = n;
}

void pb_get(uint8_t n, char *name, char *num) {
    volatile uint8_t *p = rec_ptr(n + 1);
    uint8_t i;
    for (i = 0; i < PB_NAME_LEN; i++) name[i] = p[i];
    name[PB_NAME_LEN] = 0;
    for (i = 0; i < PB_NUM_LEN; i++)  num[i] = p[PB_NAME_LEN + i];
    num[PB_NUM_LEN] = 0;
}

uint8_t pb_add(const char *name, const char *num) {
    uint8_t n = pb_count();
    volatile uint8_t *p;
    uint8_t i;
    if (n >= PB_MAX) return 0;
    p = rec_ptr(n + 1);
    for (i = 0; i < PB_NAME_LEN; i++) { p[i] = name[i]; if (!name[i]) break; }
    for (; i < PB_NAME_LEN; i++) p[i] = 0;
    for (i = 0; i < PB_NUM_LEN; i++)  { p[PB_NAME_LEN + i] = num[i]; if (!num[i]) break; }
    for (; i < PB_NUM_LEN; i++) p[PB_NAME_LEN + i] = 0;
    set_count(n + 1);
    return 1;
}

/* ---- UI ------------------------------------------------------------------ */
static void clrscr(void) {
    uint8_t y;
    for (y = 0; y < 18; y++) { gotoxy(0, y); printf("                    "); }
    gotoxy(0, 0);
}

static void putn(const char *s, uint8_t n) {        /* print up to n chars */
    while (n-- && *s) putchar(*s++);
}

static void draw_list(uint8_t top) {
    char name[PB_NAME_LEN + 1], num[PB_NUM_LEN + 1];
    uint8_t n = pb_count(), y, i;
    clrscr();
    gotoxy(0, 0); printf("PHONEBOOK %u/%u", (unsigned)n, (unsigned)PB_MAX);
    for (y = 0; y < 6; y++) {
        i = top + y;
        if (i >= n) break;
        pb_get(i, name, num);
        gotoxy(0, 2 + y * 2); printf("%u ", (unsigned)(i + 1)); putn(name, 17);
        gotoxy(2, 3 + y * 2); putn(num, 16);
    }
    gotoxy(0, 16); printf("App7 add  Up/Dn");
    gotoxy(0, 17); printf("Esc back");
}

/* Read a line from the keyboard into buf (NUL-terminated). ESC clears it. */
static void pb_input(const char *prompt, char *buf, uint8_t maxlen) {
    uint8_t len = 0, num_mode = 0, code;
    char ch;
    clrscr();
    gotoxy(0, 0); printf("%s", prompt);
    gotoxy(0, 2);
    for (;;) {
        wait_vbl_done();
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;
        if (code == WB_KEY_ENTER)  break;
        if (code == WB_KEY_ESC) { len = 0; break; }
        if (code == WB_KEY_NUM)  { num_mode ^= 1; continue; }
        if (code == WB_KEY_CAPS) { num_mode = 0;  continue; }
        if (code == WB_KEY_BACKSPACE) {
            if (len) { len--; gotoxy(len % 20, 2 + len / 20); putchar(' '); gotoxy(len % 20, 2 + len / 20); }
            continue;
        }
        ch = (code == WB_KEY_SPACE) ? ' ' : wb_scancode_to_ascii(code, num_mode);
        if (ch && len < maxlen) { buf[len++] = ch; putchar(ch); }
    }
    buf[len] = 0;
}

void pb_screen(void) {
    char name[PB_NAME_LEN + 1], num[PB_NUM_LEN + 1];
    uint8_t top = 0, code;
    pb_init();
    draw_list(top);
    for (;;) {
        wait_vbl_done();
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;
        switch (code) {
            case WB_KEY_ESC:
                clrscr();
                return;
            case WB_KEY_DOWN:
                if ((uint8_t)(top + 6) < pb_count()) { top++; draw_list(top); }
                break;
            case WB_KEY_UP:
                if (top) { top--; draw_list(top); }
                break;
            case WB_KEY_DATABASE:                 /* App-7 = add a new entry */
                pb_input("Name:", name, PB_NAME_LEN);
                if (name[0]) {
                    pb_input("Number:", num, PB_NUM_LEN);
                    pb_add(name, num);
                }
                draw_list(top);
                break;
        }
    }
}
