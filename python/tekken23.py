#
# Tekken 2 / Tekken 3 (PS1) save decoder, checksum fixer and cheat helpers for Apollo
# Format info from the game-tools-collection save editor (tekken-2 / tekken-3 templates)
#
# The game data is the 0x200-byte block at file offset 0x200 (raw PS1 save,
# starting at "SC"). It is obfuscated with a rolling cipher:
#   plain[i] = enc[i] - (enc[i-1] * 5 + 1)    for i = 1..0x1FF
#   enc[i]   = plain[i] + enc[i-1] * 5 + 1
# (i relative to 0x200, enc[i-1] is the previous *encoded* byte.)
# Byte 0 is stored as is: it is the checksum, plain[0] = -sum(plain[1..0x1FF]).
#
# Usage, one step per [python:] code (the file is rewritten between codes,
# so each step works on savedata as the previous code left it):
#   [python:Decrypt (Decode) Save (Required)]  tekken23.decrypt_save(savedata)
#   [python:<cheat>]                           tekken23.set_byte(savedata, 0x201, 0xFF) ...
#   [python:Update Checksum (Required)]        tekken23.update_checksum(savedata)
#   [python:Encrypt (Encode) Save (Required)]  tekken23.encrypt_save(savedata)
#
# A code that raises does not stop the later ones, so the decoded state is
# marked in the file itself: while decoded, the "SC" magic at 0x0000 is
# replaced by "TK". decrypt_save only accepts "SC" with a valid checksum,
# every later step refuses to run without "TK", and encrypt_save puts "SC"
# back. An invalid input is therefore never modified by any code.
#

BASE = 0x200
SIZE = 0x200
MAGIC = b"SC"
MARKER = b"TK"


def _checksum(data, base):
    return (-sum(data[base + 1:base + SIZE])) & 0xFF


def _require_decoded(data):
    if len(data) < BASE + SIZE or bytes(data[0:2]) != MARKER:
        raise ValueError("Save is not decoded, the Decrypt code failed or did not run")


def decrypt_save(data):
    if len(data) < BASE + SIZE or bytes(data[0:2]) != MAGIC:
        raise ValueError("Not an encoded PS1 Tekken save (already decoded?)")

    # decode into a copy first, so an invalid file is left untouched
    plain = bytearray(data[BASE:BASE + SIZE])
    prev = plain[0]
    for i in range(1, SIZE):
        enc = plain[i]
        plain[i] = (enc - (prev * 5 + 1)) & 0xFF
        prev = enc

    if plain[0] != _checksum(plain, 0):
        raise ValueError("Invalid checksum, not a valid Tekken save")

    data[BASE:BASE + SIZE] = plain
    data[0:2] = MARKER
    print("Save decoded OK")


def update_checksum(data):
    _require_decoded(data)
    data[BASE] = _checksum(data, BASE)
    print("New Checksum: 0x{:02X}".format(data[BASE]))


def encrypt_save(data):
    _require_decoded(data)
    if data[BASE] != _checksum(data, BASE):
        raise ValueError("Checksum does not match the data, run the checksum update code first")

    prev = data[BASE]
    for i in range(BASE + 1, BASE + SIZE):
        prev = (data[i] + prev * 5 + 1) & 0xFF
        data[i] = prev
    data[0:2] = MAGIC
    print("Save encoded OK")


# --- cheat helpers (file offsets inside the decoded block 0x201..0x3FF) ---

def _check_off(off, n):
    if off <= BASE or off + n > BASE + SIZE:
        raise ValueError("Offset 0x{:X} outside the Tekken data block".format(off))


def set_byte(data, off, value):
    _require_decoded(data)
    _check_off(off, 1)
    data[off] = value & 0xFF


def or_byte(data, off, mask):
    _require_decoded(data)
    _check_off(off, 1)
    data[off] |= mask & 0xFF


def set_bytes(data, off, values):
    _require_decoded(data)
    _check_off(off, len(values))
    data[off:off + len(values)] = values
