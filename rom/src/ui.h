/* ui.h — tiny console helpers shared by the ROM apps. */
#ifndef UI_H
#define UI_H

void clrscr(void);            /* clear the 20x18 text screen, cursor home */
void put_long(long v);        /* print a signed long in decimal           */

#endif /* UI_H */
