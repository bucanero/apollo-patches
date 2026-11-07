#
# The Forest (PS4) __RESUME__ save decoder/encoder by Bucanero
# based on forest_save.py (LevelSerializer save <-> raw data)
#
# __RESUME__ layout:
#   base64( HEADER | 7bit-len | "NOCOMPRESSION" + base64(RAW) | TRAILER )
#
# Decoded buffer layout (RAW at offset 0, so patch codes address it directly):
#   RAW | HEADER | TRAILER | u32 LE len(HEADER) | u32 LE len(TRAILER)
#
# The 7-bit length prefix is recomputed on encode, so RAW can change size.
#

import gc
import ubinascii
import ustruct as struct

MARK = b"NOCOMPRESSION"
B64_CHARS = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


def rd7(b, p):
    n = s = 0
    while True:
        c = b[p]
        p += 1
        n |= (c & 0x7F) << s
        s += 7
        if not c & 0x80:
            return n, p


def wr7(n):
    out = bytearray()
    while True:
        c = n & 0x7F
        n >>= 7
        if n:
            out.append(c | 0x80)
        else:
            out.append(c)
            return bytes(out)


def b64encode(data):
    enc = ubinascii.b2a_base64(data)
    if isinstance(enc, str):
        enc = enc.encode()
    return enc.rstrip(b"\n")


def find_payload(o, i):
    """Find the 7-bit length prefix that ends right before MARK at offset i.
    Returns (prefix_start, payload_len) or None."""

    for k in range(1, 6):
        s = i - k
        if s < 0:
            break
        L, p = rd7(o, s)
        end = i + L
        # payload = MARK + base64, so its length is 13 + 4*n
        if p != i or end > len(o) or (L - len(MARK)) % 4 or o[s:i] != wr7(L):
            continue
        # payload must end on a non-base64 byte (start of trailer)
        if end < len(o) and B64_CHARS.find(bytes([o[end]])) >= 0:
            continue
        return s, L
    return None


def theforest_decode(data):
    """Decode a __RESUME__ save into RAW | HEADER | TRAILER | footer"""

    o = ubinascii.a2b_base64(data)
    i = o.find(MARK)
    if i < 0:
        print("Error: NOCOMPRESSION marker not found")
        return False

    r = find_payload(o, i)
    if r is None:
        print("Error: length prefix not found")
        return False

    s, L = r
    header = o[:s]
    trailer = o[i + L:]
    raw = ubinascii.a2b_base64(o[i + len(MARK):i + L])
    del o
    gc.collect()

    print("Header : {} bytes".format(len(header)))
    print("Raw    : {} bytes".format(len(raw)))
    print("Trailer: {} bytes".format(len(trailer)))

    data[:] = raw + header + trailer + struct.pack("<II", len(header), len(trailer))
    del raw
    gc.collect()
    return True


def theforest_encode(data):
    """Encode RAW | HEADER | TRAILER | footer back into a __RESUME__ save"""

    if len(data) < 8:
        print("Error: invalid decoded data")
        return False

    hl, tl = struct.unpack("<II", data[-8:])
    rl = len(data) - 8 - hl - tl
    if rl < 0:
        print("Error: invalid footer (header {}, trailer {})".format(hl, tl))
        return False

    header = bytes(data[rl:rl + hl])
    trailer = bytes(data[rl + hl:rl + hl + tl])
    payload = MARK + b64encode(data[:rl])
    gc.collect()

    o = header + wr7(len(payload)) + payload + trailer
    del payload
    gc.collect()

    print("Raw    : {} bytes".format(rl))
    print("Save   : {} bytes (pre-base64)".format(len(o)))

    data[:] = b64encode(o)
    del o
    gc.collect()
    return True
