/*
 * workboy_link.c — GB master-side link driver. See workboy_link.h.
 * GBDK-2020. SB_REG/SC_REG come from <gb/hardware.h>.
 */
#include <gb/gb.h>
#include <gb/hardware.h>
#include "workboy_link.h"

/*
 * One synchronous transfer with the Game Boy as master/internal clock.
 *   SC_REG bit7 = 1 : start transfer
 *   SC_REG bit0 = 1 : internal clock (we are the master)
 * On the DMG the rate is fixed at 8192 Hz (~1 ms/byte). We poll bit7 with a
 * coarse guard so a missing/unplugged keyboard can't hang the ROM.
 */
uint8_t wb_xfer(uint8_t out) {
    uint16_t guard = 0;
    SB_REG = out;
    SC_REG = 0x81;
    while ((SC_REG & 0x80) != 0) {
        if (++guard == 0) break;   /* ~65k spins ≈ well past 1 ms at DMG clk */
    }
    return SB_REG;
}

uint8_t wb_init(void) {
    uint8_t tries;
    /* Reply is pipelined by one: send 0x52 to stage it, read it next transfer. */
    for (tries = 0; tries < 16; tries++) {
        wb_xfer(WB_CMD_INIT);                       /* stage the 0x44 reply */
        if (wb_xfer(0x00) == WB_INIT_REPLY) return 1;
        delay(10);
    }
    return 0;
}

uint8_t wb_poll_key(void) {
    /* Pipelined by one: first poll stages the key, second returns it. */
    wb_xfer(WB_CMD_POLL);
    return wb_xfer(WB_CMD_POLL);
}

void wb_read_rtc(uint8_t *buf) {
    uint8_t i;
    wb_xfer(WB_CMD_RTC_RD);                 /* command; data starts next xfer */
    for (i = 0; i < WB_RTC_LEN; i++) {
        buf[i] = wb_xfer(0x00);             /* clock out filler, read RTC byte */
    }
}

void wb_write_rtc(const uint8_t *buf24) {
    uint8_t i;
    wb_xfer(WB_CMD_RTC_WR);                 /* command; 0x30 ack pipelines next */
    for (i = 0; i < 24; i++) wb_xfer(buf24[i]);
}
