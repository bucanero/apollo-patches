#
# Gran Turismo (PS1) save editor helpers for Apollo by Bucanero
# offsets and checksum from the game-tools-collection save editor
#
# Game data file ("GT" identifier). Checksum over 0x200..0x6DA3, stored as
# u32 LE at 0x6DA4:
#   high word: c1 = 0xAAAA; per byte, c1 = ((c1 + b) & 0xFFFF) ^ (b << 8)
#   low word:  c2 = 0x3770; per data bit (MSB first), c2 is shifted left,
#              XORed with 0x1021 on carry out, and the data bit is ORed in.
# The low word is computed a byte at a time with two 256-entry tables: the
# carry pattern of 8 shifts depends only on the high byte of c2.
#

import gc

try:
    import ustruct as struct
except ImportError:
    import struct

CSUM_START = 0x200
CSUM_END = 0x6DA4

CREDITS = 0x204         # u32; Cr on US/EU, units of 100 yen on JP
LICENSES = 0x2D54       # 3 licenses x 8 tests, u8: 3 = Gold
RACES = 0x426C          # 22 GT mode events, u8: 1 = Gold
ARCADE = 0x6CF8         # 8 courses x 4 bytes: A/B/C class, bits 0-2 = Easy/Normal/Hard


def _tables():
    poly, mask = [], []
    for h in range(256):
        c, m = h << 8, 0
        for k in range(8):
            c <<= 1
            if c & 0x10000:
                c ^= 0x11021
            else:
                m |= 0x80 >> k
        poly.append(c & 0xFFFF)
        mask.append(m)
    return poly, mask


def checksum(data):
    poly, mask = _tables()
    c1, c2 = 0xAAAA, 0x3770
    for i in range(CSUM_START, CSUM_END):
        b = data[i]
        c1 = ((c1 + b) & 0xFFFF) ^ (b << 8)
        h = c2 >> 8
        c2 = ((c2 & 0xFF) << 8) ^ poly[h] ^ (b & mask[h])
    gc.collect()
    return (c1 << 16) | c2


def fix(data):
    struct.pack_into("<I", data, CSUM_END, checksum(data))
    print("[*] Gran Turismo checksum updated")


def set_credits(data, value):
    struct.pack_into("<I", data, CREDITS, value)


def gold_licenses(data):
    for i in range(24):
        data[LICENSES + i] = 3


def gold_races(data):
    for i in range(22):
        data[RACES + i] = 1


def arcade_clear(data):
    for i in range(8):
        for j in range(3):
            data[ARCADE + i * 4 + j] |= 0x07
