#
# Soulcalibur II (PS2) save decrypter, checksum fixer and cheats for Apollo
# Algorithm from the game-tools-collection save editor (soulcalibur-ii template)
#
# File layout (<code>SC2 and its copy <code>SC2_1, 0x2000 bytes each):
#   0x0000-0x1FF5  payload, XORed with a 16-bit LCG keystream
#   0x1FF6         u16 LE key = rol16(((0xA2F1 + 7 * sum(plain payload)) & 0xFFFF) ^ 0xEB7D, 3)
#   0x1FF8         8-byte tag: "BESTGAME" XORed with a stream seeded by the key
# The keystream seed is ror16(key, 3) ^ 0xEB7D, so every edit changes the key
# and the whole payload has to be re-encrypted.
#
# Usage, one step per [python:] code (the file is rewritten between codes,
# so each step works on savedata as the previous code left it):
#   [python:Decrypt SC2 (Required)]   sc2.decrypt(savedata)   validates, then decrypts
#   [python:<cheat>]                  sc2.max_gold(savedata, "SLES51799") ...
#   [python:Update ... (Required)]    sc2.fix(savedata)       new key + tag (tag kept inverted)
#   [python:Encrypt SC2 (Required)]   sc2.encrypt(savedata)   real tag, encrypt
#

import gc

FILE_SIZE = 0x2000
DATA_SIZE = 0x1FF6
KEY_OFF = 0x1FF6
TAG_OFF = 0x1FF8
TAG_TEXT = b"BESTGAME"

# Template offsets are written for the EU release; the other releases store
# the same fields 1 (US, Korea) or 3 (Japan) bytes earlier.
REGION_SHIFT = {
    "SLES51799": 0,
    "SLUS20643": -1,
    "SCKA20016": -1,
    "SLPS25230": -3,
}


def _ror16(x, n):
    return ((x >> n) | (x << (16 - n))) & 0xFFFF


def _rol16(x, n):
    return ((x << n) | (x >> (16 - n))) & 0xFFFF


def _get_key(data):
    return data[KEY_OFF] | (data[KEY_OFF + 1] << 8)


def _xor_stream(buf, key):
    x = _ror16(key, 3) ^ 0xEB7D
    for i in range(DATA_SIZE):
        buf[i] ^= x & 0xFF
        x = (_ror16(x, 1) * 5 + 1) & 0xFFFF


def calc_key(plain):
    s = (0xA2F1 + 7 * sum(plain[:DATA_SIZE])) & 0xFFFF
    return _rol16(s ^ 0xEB7D, 3)


def calc_tag(key):
    out = bytearray(8)
    x = key
    for i in range(8):
        out[i] = (TAG_TEXT[i] ^ x) & 0xFF
        x = (_ror16(x, 5) * 5 + 1) & 0xFFFF
    return out


def _shift(serial):
    if serial not in REGION_SHIFT:
        raise ValueError("Unknown Soulcalibur II serial {}".format(serial))
    return REGION_SHIFT[serial]


# The file is rewritten after every code, and a code that raises does not stop
# the later ones. So the decrypted state is marked in the file itself: while
# decrypted, 0x1FF8 holds the bitwise NOT of the tag for the key at 0x1FF6.
# An encrypted save always holds the tag itself, so the two states never
# overlap, and every step refuses to run on data in the wrong state (e.g. the
# cheats, fix and encrypt all stop if decrypt rejected the file).

def _inv_tag(key):
    return bytes((~b) & 0xFF for b in calc_tag(key))


def _is_decrypted(data):
    return len(data) == FILE_SIZE and bytes(data[TAG_OFF:TAG_OFF + 8]) == _inv_tag(_get_key(data))


def _require_decrypted(data):
    if not _is_decrypted(data):
        raise ValueError("Save is not decrypted, the Decrypt code failed or did not run")


def decrypt(data):
    """Validate, then decrypt the payload in place and mark the file as
    decrypted. Raises (leaving data untouched) if the file is not a valid
    encrypted Soulcalibur II save."""
    if len(data) != FILE_SIZE:
        raise ValueError("Not a Soulcalibur II save (size 0x{:X})".format(len(data)))
    key = _get_key(data)
    if bytes(data[TAG_OFF:TAG_OFF + 8]) != bytes(calc_tag(key)):
        raise ValueError("Bad BESTGAME tag, not an encrypted Soulcalibur II save")
    buf = bytearray(data[:DATA_SIZE])
    _xor_stream(buf, key)
    if calc_key(buf) != key:
        raise ValueError("Checksum mismatch, save damaged")
    data[:DATA_SIZE] = buf
    data[TAG_OFF:TAG_OFF + 8] = _inv_tag(key)
    print("* Decrypted Soulcalibur II save (key 0x{:04X})".format(key))
    gc.collect()


def fix(data):
    """Recompute the key (and its tag, kept inverted until encrypt) from the
    decrypted payload."""
    _require_decrypted(data)
    key = calc_key(data)
    data[KEY_OFF] = key & 0xFF
    data[KEY_OFF + 1] = key >> 8
    data[TAG_OFF:TAG_OFF + 8] = _inv_tag(key)
    print("* New key 0x{:04X}".format(key))


def encrypt(data):
    """Write the tag and encrypt the payload with the key at 0x1FF6 (run fix first)."""
    _require_decrypted(data)
    key = _get_key(data)
    if calc_key(data) != key:
        raise ValueError("Key does not match the data, run the checksum update code first")
    data[TAG_OFF:TAG_OFF + 8] = calc_tag(key)
    _xor_stream(data, key)
    gc.collect()


def _put_u32(data, off, value):
    for i in range(4):
        data[off + i] = (value >> (8 * i)) & 0xFF


# --- cheats (work on decrypted data; EU offsets + region shift) ---

def max_gold(data, serial):
    _require_decrypted(data)
    _put_u32(data, 0x283 + _shift(serial), 99999900)


def max_experience(data, serial):
    _require_decrypted(data)
    # 99,999,900 = "Ultimate Edgemaster", the highest Weapon Master class
    _put_u32(data, 0x9F + _shift(serial), 99999900)


def unlock_all(data, serial):
    _require_decrypted(data)
    # characters, profiles, demos, costumes, extra modes, museum, stages, weapons
    r = _shift(serial)
    for off in range(0x1D + r, 0x62 + r):
        data[off] |= 0xAA
    data[0x62 + r] |= 0x0A


def all_chapters(data, serial):
    _require_decrypted(data)
    # Weapon Master chapters 1-16 = Cleared (4)
    r = _shift(serial)
    for off in range(0xA3 + r, 0xB3 + r):
        data[off] = 4
