# WorkBoy homebrew ROM — GBDK-2020 build
#
# Set GBDK_HOME to your GBDK-2020 install (the folder that contains bin/lcc).
#   Linux/macOS:  make GBDK_HOME=/opt/gbdk
#   Windows:      make GBDK_HOME=C:/gbdk   (use forward slashes)
#
# Output: workboy_homebrew.gb — cartridge type MBC1+RAM+BATTERY, matching the
# original WorkBoy cart's mapper (confirmed from the ROM header). Drop it on an
# EverDrive/EZ-Flash, or flash an MBC1+RAM+BAT repro cart.

GBDK_HOME ?= /opt/gbdk
LCC        = $(GBDK_HOME)/bin/lcc

# -Wl-yt0x03 : cartridge type = MBC1+RAM+BATTERY
# -Wl-ya4    : 4 RAM banks (32 KB battery SRAM, like the original)
# -Wl-yo8    : 8 ROM banks (128 KB, matching the original WorkBoy cart)
CARTFLAGS  = -Wl-yt0x03 -Wl-ya4 -Wl-yo8
LCCFLAGS   = $(CARTFLAGS)

SRCS = src/main.c src/workboy_link.c src/scancodes.c src/phonebook.c \
       src/ui.c src/calc.c src/clock.c
ROM  = workboy_homebrew.gb

all: $(ROM)

$(ROM): $(SRCS)
	$(LCC) $(LCCFLAGS) -o $(ROM) $(SRCS)

clean:
	-rm -f $(ROM) *.map *.sym src/*.o src/*.lst src/*.rel src/*.asm src/*.ihx
