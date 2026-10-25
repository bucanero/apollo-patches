#
# Crash Bandicoot (PS1) save editor helpers for Apollo by Bucanero
# offsets and checksum from the game-tools-collection save editor
#
# The game data block starts after the title frame and the icon frames:
#   D = 0x80 * ((savedata[2] & 0x0F) + 1)  -> 0x100 (EU), 0x200 (US/JP)
# Checksum: c = 0x12345678; for each byte b of D..D+0x7F (with the stored
# field zeroed), c = ROTL32(c + b, 3). Stored as u32 LE at D+0x7C.
#
# Every cheat updates the save preview (D+0x00: levels, gem and key counts),
# the completion rate shown in the memory card title, and the checksum.
#

try:
    import ustruct as struct
except ImportError:
    import struct

# (offset from D, bits) of the 26 gems and of the 2 secret level keys
GEMS = ((0x1C, 0xBE), (0x1D, 0xF7), (0x1E, 0xBD), (0x1F, 0x2F), (0x21, 0x01), (0x22, 0x04))
KEYS = ((0x21, 0x04), (0x22, 0x10))
MAX_LEVEL = 0x1F        # level progress after The Great Hall (levels cleared + 1)
TITLE_RATE = 0x12       # completion rate text in the title frame (Shift-JIS, BE)


def base(data):
    return 0x80 * ((data[2] & 0x0F) + 1)


def _bits(v):
    n = 0
    while v:
        n += v & 1
        v >>= 1
    return n


def _count(data, d, table):
    n = 0
    for off, mask in table:
        n += _bits(data[d + off] & mask)
    return n


def _set(data, d, table):
    for off, mask in table:
        data[d + off] |= mask


def checksum(data, d):
    c = 0x12345678
    for i in range(d, d + 0x7C):
        c = (c + data[i]) & 0xFFFFFFFF
        c = ((c << 3) | (c >> 29)) & 0xFFFFFFFF
    # the zeroed checksum field: four more rounds with b = 0
    for i in range(4):
        c = ((c << 3) | (c >> 29)) & 0xFFFFFFFF
    return c


def update_summary(data):
    d = base(data)
    levels = min(struct.unpack_from("<I", data, d + 4)[0], MAX_LEVEL)
    gems = _count(data, d, GEMS)
    keys = _count(data, d, KEYS)
    w = struct.unpack_from("<H", data, d)[0]
    w = (w & 0xF000) | levels | (gems << 5) | (keys << 10)
    struct.pack_into("<H", data, d, w)

    pct = (max(min(levels - 1, 28), 0) * 2 + gems + keys * 3) * 100 // 88
    text = []
    for c in "{}".format(pct):
        text.append(0x824F + ord(c) - 0x30)
    text += [0x8193, 0x816A, 0x0000]
    for i in range(len(text)):
        struct.pack_into(">H", data, TITLE_RATE + i * 2, text[i])


def fix(data):
    d = base(data)
    update_summary(data)
    struct.pack_into("<I", data, d + 0x7C, checksum(data, d))
    print("[*] Crash Bandicoot checksum updated (data at 0x{:X})".format(d))


def all_levels(data):
    struct.pack_into("<I", data, base(data) + 4, MAX_LEVEL)


def all_gems(data):
    _set(data, base(data), GEMS)


def all_keys(data):
    _set(data, base(data), KEYS)


def complete(data):
    all_levels(data)
    all_gems(data)
    all_keys(data)
