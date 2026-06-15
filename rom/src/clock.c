/*
 * clock.c — live clock from the keyboard's RTC, with set (App-1 / scancode 0x01).
 * Displays HH:MM:SS + DD/MM read over the link; pressing 'S' lets you type a new
 * HHMMSS which is written back via the RTC-write command (date preserved).
 */
#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdio.h>
#include "clock.h"
#include "ui.h"
#include "workboy_link.h"
#include "scancodes.h"

static int8_t cdigit(uint8_t code) {
    switch (code) {
        case 0x11: return 1; case 0x12: return 2; case 0x13: return 3;
        case 0x1C: return 4; case 0x1D: return 5; case 0x1E: return 6;
        case 0x28: return 7; case 0x29: return 8; case 0x2A: return 9;
        case 0x33: return 0;
        default:   return -1;
    }
}

static void show_time(void) {
    uint8_t r[WB_RTC_LEN];
    wb_read_rtc(r);
    /* RTC frame is ASCII digit pairs: hh@8-9, mm@6-7, ss@4-5, day@10-11, mon@12-13 */
    gotoxy(0, 4); printf("%c%c:%c%c:%c%c", r[8], r[9], r[6], r[7], r[4], r[5]);
    gotoxy(0, 6); printf("%c%c/%c%c", r[10], r[11], r[12], r[13]);
}

static void clock_set(void) {
    uint8_t cur[WB_RTC_LEN], buf[24], n = 0, code, i;
    char d[6];
    int8_t v;

    wb_read_rtc(cur);                          /* keep the current date */
    clrscr();
    gotoxy(0, 0); printf("SET HHMMSS:");
    gotoxy(0, 2);
    while (n < 6) {
        wait_vbl_done();
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;
        if (code == WB_KEY_ESC) return;
        v = cdigit(code);
        if (v >= 0) { d[n++] = (char)('0' + v); putchar('0' + v); }
    }
    for (i = 0; i < 24; i++) buf[i] = 0;
    buf[6]  = 0x04;
    buf[10] = (uint8_t)(((d[0]-'0') << 4) | (d[1]-'0'));     /* hours   BCD */
    buf[9]  = (uint8_t)(((d[2]-'0') << 4) | (d[3]-'0'));     /* minutes BCD */
    buf[8]  = (uint8_t)(((d[4]-'0') << 4) | (d[5]-'0'));     /* seconds BCD */
    buf[11] = (uint8_t)(((cur[10]-'0') << 4) | (cur[11]-'0'));   /* day   */
    buf[12] = (uint8_t)(((cur[12]-'0') << 4) | (cur[13]-'0'));   /* month */
    buf[21] = (uint8_t)((cur[30]-0x30) * 16 + (cur[31]-0x30));   /* years since 1900 */
    wb_write_rtc(buf);
}

static void header(void) {
    clrscr();
    gotoxy(0, 0);  printf("CLOCK");
    gotoxy(0, 16); printf("S=set Esc=back");
    show_time();
}

void clock_screen(void) {
    uint8_t code, tick = 0;
    header();
    for (;;) {
        wait_vbl_done();
        if ((++tick & 0x1F) == 0) show_time();    /* refresh a couple times/sec */
        code = wb_poll_key();
        if (code == WB_NOKEY) continue;
        if (code == WB_KEY_ESC) { clrscr(); return; }
        if (code == 0x1D) { clock_set(); header(); }   /* 'S' key */
    }
}
