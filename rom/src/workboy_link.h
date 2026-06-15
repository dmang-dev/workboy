/*
 * workboy_link.h — Game Boy (master) side of the WorkBoy link protocol.
 * Clean-room: implemented from WORKBOY_PROTOCOL.md, not from the leaked ROM.
 *
 * The Game Boy is the serial MASTER (internal clock). Each transfer shifts one
 * byte out and one byte in; the keyboard slave's response to command N appears
 * on transfer N+1 (pipelined by one), so the helpers below send a command and
 * read the result on the following transfer.
 */
#ifndef WORKBOY_LINK_H
#define WORKBOY_LINK_H

#include <stdint.h>

#define WB_CMD_INIT    0x52  /* 'R' -> keyboard replies 0x44, goes ACTIVE   */
#define WB_CMD_POLL    0x4F  /* 'O' -> keyboard returns one key scan code   */
#define WB_CMD_RTC_RD  0x44  /* 'D' -> keyboard streams 42 RTC bytes        */
#define WB_CMD_RTC_WR  0x57  /* 'W' -> keyboard acks 0x30, then absorbs data */
#define WB_INIT_REPLY  0x44
#define WB_WR_ACK      0x30
#define WB_NOKEY       0x00  /* GBE+ convention (SameBoy uses 0xFF)         */
#define WB_RTC_LEN     42

/* One master serial transfer. Sends `out`, returns the byte shifted in. */
uint8_t wb_xfer(uint8_t out);

/* Run the init handshake. Returns 1 if the keyboard answered 0x44, else 0. */
uint8_t wb_init(void);

/* Poll the keyboard once. Returns the current scan code (WB_NOKEY if none). */
uint8_t wb_poll_key(void);

/* Read the 42-byte RTC block into buf[42]. */
void wb_read_rtc(uint8_t *buf);

/* Write the 24-byte RTC payload (sets the keyboard's clock). */
void wb_write_rtc(const uint8_t *buf24);

#endif /* WORKBOY_LINK_H */
