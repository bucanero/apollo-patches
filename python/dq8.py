#
# Dragon Quest VIII - Journey of the Cursed King (PS2) cheats & checksum fixer by Bucanero
# offsets from game-tools-collection save editor
#
# Data file B?SL??-?????dq8_N (0x5CE0 bytes), all values little-endian.
# Checksum: u32 at 0x08 = sum of (byte % 0xFF) for every 0x40th byte,
# from 0x40 up to 0x2E40 (the game's loop runs while offset < 0x2E80).
#

import gc
import ubinascii
import ustruct as struct

CHECKSUM_OFFSET = 0x08
CHECKSUM_START = 0x40
CHECKSUM_END = 0x2E80
CHECKSUM_STEP = 0x40

# Party table: Hero, Yangus, Jessica, Angelo
PARTY_BASE = 0xA70
PARTY_STRIDE = 0x68
HERO, YANGUS, JESSICA, ANGELO = 0, 1, 2, 3

# Item ids that exist (0x001..0x182), as a bit list at 0x14A8 (bit = id & 7)
COLLECTED_OFFSET = 0x14A8
COLLECTED_MASK = (
    "feffffffffffffffdffff7effdfffffbfffffdffff7fffffffffef7fffe7"
    "7ffff9fffff7efe7f7df3df8fbeffffbbfff07"
)


def calc_checksum(data):
    csum = 0
    for i in range(CHECKSUM_START, CHECKSUM_END, CHECKSUM_STEP):
        csum += data[i] % 0xFF
    return csum & 0xFFFFFFFF


def fix(data):
    csum = calc_checksum(data)
    struct.pack_into("<I", data, CHECKSUM_OFFSET, csum)
    print("* DQ8 checksum updated: 0x{:08X}".format(csum))
    gc.collect()


def _char(c, off):
    return PARTY_BASE + c * PARTY_STRIDE + off


def max_gold(data):
    struct.pack_into("<I", data, 0xA40, 99999999)


def hero_level_99(data):
    # level is stored as level - 1; experience for level 99 is 6,931,659
    struct.pack_into("<H", data, _char(HERO, 0x10), 98)
    struct.pack_into("<I", data, _char(HERO, 0x18), 6931659)


def jessica_max_hp(data):
    struct.pack_into("<H", data, _char(JESSICA, 0x00), 999)
    struct.pack_into("<H", data, _char(JESSICA, 0x04), 999)


def jessica_fisticuffs(data):
    # skill points 1..5 at +0x3A..+0x42; Fisticuffs is the 4th (+0x40)
    struct.pack_into("<H", data, _char(JESSICA, 0x40), 100)


def max_battle_records(data):
    # battles, monsters defeated, victories
    for off in (0x1740, 0x1744, 0x174C):
        struct.pack_into("<I", data, off, 999999)


def all_items_collected(data):
    mask = ubinascii.unhexlify(COLLECTED_MASK)
    for i in range(len(mask)):
        data[COLLECTED_OFFSET + i] |= mask[i]
