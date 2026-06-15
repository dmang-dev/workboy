/* ui.c — see ui.h. */
#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdio.h>
#include "ui.h"

void clrscr(void) {
    uint8_t y;
    for (y = 0; y < 18; y++) { gotoxy(0, y); printf("                    "); }
    gotoxy(0, 0);
}

void put_long(long v) {
    char b[12];
    uint8_t i = 0, neg = (v < 0);
    unsigned long u = neg ? (unsigned long)(-v) : (unsigned long)v;
    if (!u) b[i++] = '0';
    while (u) { b[i++] = (char)('0' + (u % 10)); u /= 10; }
    if (neg) putchar('-');
    while (i) putchar(b[--i]);
}
