/*
 * workboy_keyboard.c — WorkBoy-compatible keyboard controller (ATmega328P @ 5V)
 * -----------------------------------------------------------------------------
 * Acts as the passive SPI SLAVE for a Game Boy DMG/GBC link port. The Game Boy
 * is the master and supplies the clock; we shift out one response byte for each
 * command byte it clocks in. See WORKBOY_PROTOCOL.md for the full contract.
 *
 * Toolchain: avr-gcc + avr-libc + avrdude (PlatformIO board = ATmega328P).
 * Clock:     internal 8 MHz RC oscillator (no crystal). SPI-slave max is fosc/4
 *            = 2 MHz, far above the GB's ~8192 Hz / 500 kHz-max external clock.
 * Fuses:     internal 8 MHz, BOD on, no clock divide (CKDIV8 off).
 * Program:   via the 2x3 ISP header (USBasp / Arduino-as-ISP). Note the ISP pins
 *            are shared with the link SPI pins — program BEFORE attaching the GB.
 *
 * Electrical: 5V-native AVR connects DIRECTLY to the 5V link (no level shifter).
 *   GB SO (pin2, GB output) -> 220R -> MOSI (PB3)   [we sample]
 *   GB SI (pin3, GB input)  <- 220R <- MISO (PB4)   [we drive]
 *   GB SC (pin5, clock)     -> 220R -> SCK  (PB5)
 *   /SS (PB2) strapped low via 10k (single peripheral, always selected)
 *   Power the board from USB-C / battery — NOT the link VCC pin.
 *
 * This is a clean-room implementation of the documented wire protocol. It does
 * not contain or derive from any leaked Nintendo code.
 */

#ifndef F_CPU
#define F_CPU 8000000UL
#endif
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <stdint.h>

/* ---- Protocol constants (flip here if hardware testing disagrees) -------- */
#define WB_CMD_INIT     0x52  /* 'R' */
#define WB_CMD_POLL     0x4F  /* 'O' */
#define WB_CMD_RTC_RD   0x44  /* 'D' */
#define WB_CMD_RTC_WR   0x57  /* 'W' */
#define WB_INIT_REPLY   0x44
#define WB_WR_ACK       0x30
#define WB_NOKEY        0x00  /* GBE+ convention; SameBoy uses 0xFF */
#define WB_RTC_RD_LEN   42
#define WB_RTC_WR_LEN   24

/* ---- Matrix geometry: 8 rows x 7 cols = 56 positions, 53 populated -------- */
#define ROWS 8
#define COLS 7
#define DEBOUNCE_STABLE 4     /* consecutive equal samples (~4 ms at 1 ms tick) */

/* SCANCODE[ROWS][COLS] is generated from layout/keymap.py (the single source of
 * truth shared with the PCB netlist and the case). Regenerate it with:
 *     python layout/gen_layout.py
 * Each reading-order key i sits at matrix cell (i/COLS, i%COLS). */
#include "scancode_map.h"

/* ---- Shared state (ISR <-> main loop) ------------------------------------ */
typedef enum { ST_IDLE, ST_ACTIVE, ST_RTC_RD, ST_RTC_WR } wb_state_t;
static volatile wb_state_t  state       = ST_IDLE;
static volatile uint8_t     reported_key = WB_NOKEY;   /* most-recent key */
static volatile uint8_t     key_consumed = 1;          /* repeat suppression */
static volatile uint8_t     rtc_idx      = 0;
static volatile uint8_t     rtc_buf[WB_RTC_RD_LEN] = { [0 ... WB_RTC_RD_LEN - 1] = '0' };
static volatile uint8_t     wr_buf[WB_RTC_WR_LEN];      /* RTC-write payload    */
static void apply_rtc_write(void);                       /* defined below        */

/* ---- SPI slave: SPI Transfer Complete ISR -------------------------------- */
ISR(SPI_STC_vect)
{
    uint8_t cmd = SPDR;          /* byte just clocked in by the Game Boy */
    uint8_t out = WB_NOKEY;      /* byte returned on the NEXT transfer    */

    switch (state) {
    case ST_IDLE:
        if (cmd == WB_CMD_INIT) { out = WB_INIT_REPLY; state = ST_ACTIVE; }
        break;
    case ST_ACTIVE:
        switch (cmd) {
        case WB_CMD_POLL:
            out = key_consumed ? WB_NOKEY : reported_key;
            key_consumed = 1;                 /* report each press once */
            break;
        case WB_CMD_RTC_RD:
            rtc_idx = 0; state = ST_RTC_RD; out = rtc_buf[rtc_idx++];
            break;
        case WB_CMD_RTC_WR:
            rtc_idx = 0; state = ST_RTC_WR; out = WB_WR_ACK;
            break;
        case WB_CMD_INIT:
            out = WB_INIT_REPLY;
            break;
        }
        break;
    case ST_RTC_RD:
        out = rtc_buf[rtc_idx++];
        if (rtc_idx >= WB_RTC_RD_LEN) state = ST_ACTIVE;
        break;
    case ST_RTC_WR:
        if (rtc_idx < WB_RTC_WR_LEN) wr_buf[rtc_idx] = cmd;
        if (++rtc_idx >= WB_RTC_WR_LEN) { apply_rtc_write(); state = ST_ACTIVE; }
        break;
    }
    SPDR = out;                  /* stage response for transfer N+1 */
}

/* ---- 1 ms scan tick -------------------------------------------------------*/
static volatile uint8_t scan_tick = 0;
ISR(TIMER0_COMPA_vect) { scan_tick = 1; }

/* ---- Drive one row LOW, read 7 columns (active-low, internal pull-ups) ---- */
static uint8_t col_count[ROWS][COLS];   /* debounce integrators */
static uint8_t key_state[ROWS][COLS];   /* debounced pressed flag */

/* Pin map locked by kicad/workboy.net: ROW0..7 = PORTD (PD0..PD7);
   COL0..5 = PC0..PC5; COL6 = PB0. Diode anode->COL, cathode->switch->ROW. */
static void drive_row(uint8_t r) {
    DDRD  = (uint8_t)(1u << r);   /* only row r is an output...        */
    PORTD = 0x00;                 /* ...driven LOW; all others hi-Z    */
}
static uint8_t read_col(uint8_t c) {
    if (c < 6) return (PINC >> c) & 1u;     /* COL0..5 = PC0..PC5 */
    return (PINB >> PB0) & 1u;              /* COL6     = PB0     */
}

static void scan_and_debounce(void) {
    for (uint8_t r = 0; r < ROWS; r++) {
        drive_row(r);
        _delay_us(5);                 /* let columns settle through the pull-ups */
        for (uint8_t c = 0; c < COLS; c++) {
            uint8_t pressed = (read_col(c) == 0);
            if (pressed == key_state[r][c]) { col_count[r][c] = 0; continue; }
            if (++col_count[r][c] >= DEBOUNCE_STABLE) {
                col_count[r][c] = 0;
                key_state[r][c] = pressed;
                if (pressed) {
                    uint8_t code = pgm_read_byte(&SCANCODE[r][c]);
                    if (code != 0x00) {               /* atomic handoff to ISR */
                        uint8_t s = SREG; cli();
                        reported_key = code; key_consumed = 0;
                        SREG = s;
                    }
                }
            }
        }
    }
}

/* ---- RTC: 1 Hz software clock formatted into rtc_buf on demand ------------ */
static volatile uint8_t sec, min, hr, day = 1, mon = 1; static volatile uint16_t yr = 2026;
static volatile uint8_t rtc_dirty = 1;          /* reformat the RTC frame when set */
ISR(TIMER1_COMPA_vect) {
    if (++sec >= 60) { sec = 0; if (++min >= 60) { min = 0; if (++hr >= 24) hr = 0; } }
    rtc_dirty = 1;
}

/* Two ASCII digits ('0'..'9') of v (0..99) into p[0],p[1]. */
static inline void put2(uint8_t *p, uint8_t v) {
    p[0] = '0' + (uint8_t)((v / 10) % 10);
    p[1] = '0' + (uint8_t)(v % 10);
}

/*
 * Build the 42-byte RTC frame in the EXACT format the WorkBoy ROM expects
 * (verified against GBE+ workboy_get_time): every field is ASCII digits and the
 * whole buffer is filled with '0' (0x30) — a 0x00 byte anywhere signals an error.
 * Race-safe: snapshot the clock and format into a local, then copy into the
 * shared buffer with interrupts off, and never mid-read.
 */
static void format_rtc(void) {
    uint8_t tmp[WB_RTC_RD_LEN];
    uint8_t s, m, h, d, mo, years, i;
    uint8_t sreg;

    sreg = SREG; cli();                 /* atomic snapshot of the clock */
    s = sec; m = min; h = hr; d = day; mo = mon;
    years = (uint8_t)(yr - 1900);
    SREG = sreg;

    for (i = 0; i < WB_RTC_RD_LEN; i++) tmp[i] = '0';   /* non-zero fill */
    put2(&tmp[0x04], s);                /* seconds (ASCII) */
    put2(&tmp[0x06], m);                /* minutes */
    put2(&tmp[0x08], h);                /* hours   */
    put2(&tmp[0x0A], d);                /* day     */
    put2(&tmp[0x0C], mo);               /* month   */
    tmp[0x1E] = 0x30 + (years / 16);    /* year MSB (GBE+ formula) */
    tmp[0x1F] = 0x30 + (years % 16);    /* year LSB */

    sreg = SREG; cli();
    if (state != ST_RTC_RD)             /* don't clobber a frame being read out */
        for (i = 0; i < WB_RTC_RD_LEN; i++) rtc_buf[i] = tmp[i];
    SREG = sreg;
}

/* Apply a 24-byte RTC-write payload (GBE+-style positions; BCD time/date). */
static inline uint8_t bcd2(uint8_t b) { return (uint8_t)((b >> 4) * 10 + (b & 0x0F)); }
static void apply_rtc_write(void) {
    sec = bcd2(wr_buf[8]);  min = bcd2(wr_buf[9]);  hr = bcd2(wr_buf[10]);
    day = bcd2(wr_buf[11] & 0x3F);  mon = bcd2(wr_buf[12] & 0x1F);
    yr  = (uint16_t)(1900u + wr_buf[21]);
    rtc_dirty = 1;
}

/* ---- Init ----------------------------------------------------------------- */
static void spi_slave_init(void) {
    /* MISO (PB4) output, MOSI/SCK/SS inputs. SS pulled low externally. */
    DDRB |= (1 << PB4);
    DDRB &= ~((1 << PB3) | (1 << PB5) | (1 << PB2));
    /* SPE | SPIE | CPHA (Mode 1). DORD=0 -> MSB first. */
    SPCR = (1 << SPE) | (1 << SPIE) | (1 << CPHA);
    SPDR = WB_NOKEY;                  /* safe first byte */
}
static void timer0_1ms_init(void) {   /* 8 MHz / 64 / 125 = 1 kHz */
    TCCR0A = (1 << WGM01); OCR0A = 124; TCCR0B = (1 << CS01) | (1 << CS00);
    TIMSK0 = (1 << OCIE0A);
}
static void timer1_1hz_init(void) {   /* 8 MHz / 1024 / 7812 ~= 1 Hz */
    TCCR1B = (1 << WGM12) | (1 << CS12) | (1 << CS10); OCR1A = 7811;
    TIMSK1 = (1 << OCIE1A);
}
static void io_init(void) {
    /* Rows = PORTD (PD0..PD7): start all hi-Z (input, no pull-up). */
    DDRD = 0x00; PORTD = 0x00;
    /* Cols 0..5 = PC0..PC5: input + pull-up. */
    DDRC &= ~0x3Fu; PORTC |= 0x3Fu;
    /* Col 6 = PB0: input + pull-up. */
    DDRB &= ~(1u << PB0); PORTB |= (1u << PB0);
    /* Status LEDs PB6 (CAPS) / PB7 (NUM): outputs, start off.
       (Requires internal-RC fuse so PB6/PB7 are GPIO, not XTAL.) */
    DDRB |= (1u << PB6) | (1u << PB7);
    PORTB &= ~((1u << PB6) | (1u << PB7));
    /* SPI pins set in spi_slave_init(); /SS (PB2) held low externally by R2. */
}

int main(void) {
    io_init(); spi_slave_init(); timer0_1ms_init(); timer1_1hz_init();
    sei();
    for (;;) {
        if (scan_tick) { scan_tick = 0; scan_and_debounce(); }
        if (rtc_dirty) { rtc_dirty = 0; format_rtc(); }
    }
}
