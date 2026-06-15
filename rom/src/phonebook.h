/*
 * phonebook.h — battery-backed phone book stored in the cart's 32 KB SRAM.
 * Clean-room (our own record layout; not the leaked ROM's format).
 */
#ifndef PHONEBOOK_H
#define PHONEBOOK_H

#include <stdint.h>

#define PB_NAME_LEN  100      /* name + address, like the original's 120     */
#define PB_NUM_LEN   24       /* telephone number                            */
#define PB_ENTRY     128      /* record size; 8192/128 = 64 records per bank */
#define PB_MAX       255      /* 255 * 128 = 32640 B -> spans all four banks  */

void    pb_init(void);                              /* enable + validate SRAM */
uint8_t pb_count(void);
void    pb_get(uint8_t n, char *name, char *num);   /* 0-based read           */
uint8_t pb_add(const char *name, const char *num);  /* 1 = stored, 0 = full   */
void    pb_screen(void);                            /* interactive UI; ESC exits */

#endif /* PHONEBOOK_H */
