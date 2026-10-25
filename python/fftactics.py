#
# Final Fantasy Tactics (PS1) cheats & checksum fixer for Apollo
# offsets from the game-tools-collection save editor, confirmed on real saves
#
# Raw PS1 save (one slot per file, FFTA..FFTO, 0x2000 bytes):
#   0x118  8-byte parity checksum over 0x0000..0x1DFF
#   0x484  20 units, 0xE0 bytes each (0..15 party, 16..19 guests)
#   0x1604 inventory, one count byte per item id (0x01..0xFD)
#   0x1934 war funds (u32 LE)
#

import gc

CHECKSUM_OFS = 0x118
CHECKSUM_BLOCKS = 60
BLOCK_SIZE = 0x80

UNIT_BASE = 0x484
UNIT_SIZE = 0xE0
UNIT_COUNT = 20

U_TYPE = 0x00          # 0x00 = empty, 0x82 = monster
U_REG = 0x01           # registered number, 0xFF = empty / dismissed
U_EXP = 0x15
U_LEVEL = 0x16
U_BRAVE = 0x17
U_FAITH = 0x18
U_ABILITIES = 0x2B     # 19 jobs x 3 bytes of learned-ability bits
U_ABILITIES_LEN = 57
U_JP = 0x6E            # 20 x u16 LE, current JP per job
U_TOTAL_JP = 0x96      # 20 x u16 LE, total JP per job
JOBS = 20

TYPE_MONSTER = 0x82

PREVIEW_LEVEL = 0x113  # level of unit 0 shown on the load screen

INVENTORY = 0x1604
ITEM_FIRST = 0x01
ITEM_LAST = 0xFD

WAR_FUNDS = 0x1934

# World map: 43 places (bits 0x00..0x2A from 0x1AB4) and the routes
# (0x1AB9 bit 4 .. 0x1ABF bit 3)
WORLD_MAP = ((0x1AB4, 0xFF), (0x1AB5, 0xFF), (0x1AB6, 0xFF), (0x1AB7, 0xFF),
             (0x1AB8, 0xFF), (0x1AB9, 0xF7), (0x1ABA, 0xFF), (0x1ABB, 0xFF),
             (0x1ABC, 0xFF), (0x1ABD, 0xFF), (0x1ABE, 0xFF), (0x1ABF, 0x0F))

# Brave Story "Record" events: 0x1AAB bit 4 .. 0x1AB3 bit 3
BRAVE_RECORD = ((0x1AAB, 0xF0), (0x1AAC, 0xFF), (0x1AAD, 0xFF), (0x1AAE, 0xFF),
                (0x1AAF, 0xFF), (0x1AB0, 0xFF), (0x1AB1, 0xFF), (0x1AB2, 0xFF),
                (0x1AB3, 0x0F))

# Brave Story "Person" entries: 4-bit page counts from 0x1B10 (index, max)
PERSONS_OFS = 0x1B10
PERSONS = ((0x00, 6), (0x01, 7), (0x02, 6), (0x03, 4), (0x04, 3), (0x05, 4),
           (0x06, 4), (0x07, 4), (0x08, 4), (0x09, 4), (0x0A, 3), (0x0B, 3),
           (0x0C, 3), (0x0D, 2), (0x0E, 2), (0x0F, 3), (0x10, 3), (0x11, 2),
           (0x14, 2), (0x16, 2), (0x17, 4), (0x18, 2), (0x19, 2), (0x1A, 3),
           (0x1C, 2), (0x1D, 3), (0x1E, 3), (0x20, 2), (0x22, 1), (0x23, 3),
           (0x24, 3), (0x25, 2), (0x26, 2), (0x27, 1), (0x28, 3), (0x29, 1),
           (0x2A, 3), (0x2B, 1), (0x2C, 1), (0x2D, 2), (0x2E, 1), (0x2F, 3),
           (0x30, 2), (0x31, 2), (0x32, 2), (0x33, 3), (0x3D, 1), (0x3E, 1),
           (0x3F, 1))


def _parity(data, start, end):
    p = 0
    for i in range(start, end):
        p ^= data[i]
    p ^= p >> 4
    p ^= p >> 2
    p ^= p >> 1
    return p & 1


def calc_checksum(data):
    # bit i (MSB first) = parity of 0x80-byte block i, checksum field read as zero
    saved = bytes(data[CHECKSUM_OFS:CHECKSUM_OFS + 8])
    data[CHECKSUM_OFS:CHECKSUM_OFS + 8] = bytes(8)
    out = bytearray(b"\xFF" * 8)
    for i in range(CHECKSUM_BLOCKS):
        mask = 0x80 >> (i % 8)
        if _parity(data, i * BLOCK_SIZE, (i + 1) * BLOCK_SIZE):
            out[i // 8] |= mask
        else:
            out[i // 8] &= ~mask & 0xFF
    data[CHECKSUM_OFS:CHECKSUM_OFS + 8] = saved
    return out


def fix(data):
    data[CHECKSUM_OFS:CHECKSUM_OFS + 8] = calc_checksum(data)
    print("FFT checksum updated: {}".format(
        "".join("{:02X}".format(b) for b in data[CHECKSUM_OFS:CHECKSUM_OFS + 8])))
    gc.collect()


def _put16(data, ofs, value):
    data[ofs] = value & 0xFF
    data[ofs + 1] = (value >> 8) & 0xFF


def _get16(data, ofs):
    return data[ofs] | (data[ofs + 1] << 8)


def units(data):
    # offsets of the used unit slots (empty slots are type 0 / registered 0xFF)
    used = []
    for u in range(UNIT_COUNT):
        base = UNIT_BASE + u * UNIT_SIZE
        if data[base + U_TYPE] != 0 and data[base + U_REG] != 0xFF:
            used.append(base)
    return used


def set_war_funds(data, value=99999999):
    data[WAR_FUNDS:WAR_FUNDS + 4] = bytes((value & 0xFF, (value >> 8) & 0xFF,
                                           (value >> 16) & 0xFF, (value >> 24) & 0xFF))


def all_items(data, count=99):
    for item in range(ITEM_FIRST, ITEM_LAST + 1):
        data[INVENTORY + item] = count


def set_level(data, level=99):
    for base in units(data):
        data[base + U_LEVEL] = level
        data[base + U_EXP] = 0
        if base == UNIT_BASE:
            data[PREVIEW_LEVEL] = level


def set_brave_faith(data, brave=97, faith=90):
    for base in units(data):
        data[base + U_BRAVE] = brave
        data[base + U_FAITH] = faith


def set_jp(data, jp=9999):
    for base in units(data):
        if data[base + U_TYPE] == TYPE_MONSTER:
            continue
        for j in range(JOBS):
            _put16(data, base + U_JP + j * 2, jp)
            if _get16(data, base + U_TOTAL_JP + j * 2) < jp:
                _put16(data, base + U_TOTAL_JP + j * 2, jp)


def learn_all_abilities(data):
    for base in units(data):
        if data[base + U_TYPE] == TYPE_MONSTER:
            continue
        ofs = base + U_ABILITIES
        data[ofs:ofs + U_ABILITIES_LEN] = b"\xFF" * U_ABILITIES_LEN


def unlock_world_map(data):
    for ofs, mask in WORLD_MAP:
        data[ofs] |= mask


def unlock_brave_story(data):
    for ofs, mask in BRAVE_RECORD:
        data[ofs] |= mask
    for index, top in PERSONS:
        ofs = PERSONS_OFS + index // 2
        if index % 2:
            if (data[ofs] >> 4) < top:
                data[ofs] = (data[ofs] & 0x0F) | (top << 4)
        else:
            if (data[ofs] & 0x0F) < top:
                data[ofs] = (data[ofs] & 0xF0) | top
