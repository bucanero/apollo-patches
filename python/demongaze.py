#
# Demon Gaze EXTRA (CUSA27746) slot save unpack/repack
# ported from dgs_aio.py (constants from Il2CppUserAssemblies.elf)
#
# Slot saves DGAZ_%02d.SAV / DGAUTO.SAV:
#   0x00  "DGS\0" magic
#   0x56  u8  version
#   0x57  u8  compressed flag (1 = LZ payload, 0 = unpacked by this script)
#   0x60  u32 uncompressed size
#   0x64  u32 XOR of the LE u32 words of the compressed payload
#   0x68  payload
#
# Payload: u32 size, u32 token count, then groups of 16 tokens, each group
# led by a u16 flag word. A literal token is two bytes mapped through
# SUB_TABLE; a match token is (dist << 7) | len, counted in 16-bit words.
#
# dg_unpack() keeps the 0x68-byte header, clears the compressed flag and
# appends the raw data, so the cheat offsets are 0x68 + raw offset.
# dg_pack() recompresses and fixes the size and checksum. Each one checks the
# flag first, so running a code twice is harmless.
#
# DGSYS.SAV (system save) is neither compressed nor checksummed.
#

import gc
import ubinascii
import ustruct as struct

SUB_TABLE = ubinascii.unhexlify(
    "dce6728ff41ec98736d481f292d3ceaf52f65cc422bc27fb97c2edccb865b079"
    "7f57073a0e5ab702d9d85d9d56df49aa2ce0dd001a94932959d67a31fc3dbd41"
    "1180de60b43b69066c61a17efa6ed1aba21f3983eb662a76cdf93f9899e5e9e7"
    "45a0854210b650bafd6296146b4715c618a832ad3e9c5b0d1935d7c7a96840137"
    "51c0f26c5dbcf536d4eaea77b4b0be354c33cacb1908ed52e0a82b563efbb7d5f"
    "0473f89bfe5121a48d37b3175e6777b2057c25f020239a91c19e24f5be0cf116a3"
    "d04ce828a6ee2d2b8644892f70ca4dc871bf46ead2124a888be438c0f7a5589f84"
    "ec55f33309e28c746aff08301d7843484f34e195dab91b648a01cb036f")

MAGIC = b"DGS\x00"
HDR_SIZE = 0x68
OFS_FLAG = 0x57
OFS_SIZE = 0x60
OFS_CSUM = 0x64

MAX_LEN = 127
MAX_DIST = 511
CHAIN = 48


def _inv_table():
    inv = bytearray(256)
    for i in range(256):
        inv[SUB_TABLE[i]] = i
    return inv


def _check(data):
    if len(data) < HDR_SIZE or bytes(data[:4]) != MAGIC:
        raise Exception("Error: not a Demon Gaze slot save (DGS)")


def xor32(data):
    v = 0
    n = len(data) // 4
    for w in struct.unpack_from("<%dI" % n, data, 0):
        v ^= w
    return v


def _decompress(payload):
    usize, ntokens = struct.unpack_from("<II", payload, 0)
    nwords = len(payload) // 2
    words = struct.unpack_from("<%dH" % nwords, payload, 0)
    sub = SUB_TABLE

    out = bytearray(usize)
    pos = 0
    v4 = 4
    v5 = 5
    for t in range(ntokens):
        flag = words[v4] if v4 < nwords else 0
        tok = words[v5] if v5 < nwords else 0
        if not (flag >> (t & 0xF)) & 1:
            out[pos] = sub[tok & 0xFF]
            out[pos + 1] = sub[tok >> 8]
            pos += 2
        else:
            length = (tok & 0x7F) * 2
            if length:
                start = pos - (tok >> 7) * 2
                for k in range(length):
                    out[pos + k] = out[start + k]
                pos += length
        if (t + 1) & 0xF:
            v5 += 1
        else:
            v4 = v5 + 1
            v5 += 2

    if pos != usize:
        raise Exception("Error: decompressed {} bytes, expected {}".format(pos, usize))
    return out


def _compress(raw):
    if len(raw) % 2:
        raise Exception("Error: data length must be even")
    inv = _inv_table()
    n = len(raw) // 2
    words = struct.unpack("<%dH" % n, raw)
    recent = {}
    out = bytearray(struct.pack("<II", len(raw), 0))
    ntok = 0
    flags = 0
    group = bytearray()

    i = 0
    while i < n:
        best_len = 0
        best_dist = 0
        lst = recent.get(words[i])
        if lst:
            maxl = min(MAX_LEN, n - i)
            for j in reversed(lst[-CHAIN:]):
                dist = i - j
                if dist > MAX_DIST:
                    break
                l = 1
                while l < maxl and words[j + l] == words[i + l]:
                    l += 1
                if l > best_len:
                    best_len = l
                    best_dist = dist
                    if l == maxl:
                        break

        if best_len >= 2:
            flags |= 1 << (ntok & 0xF)
            group += struct.pack("<H", (best_dist << 7) | best_len)
            step = best_len
        else:
            w = words[i]
            group.append(inv[w & 0xFF])
            group.append(inv[w >> 8])
            step = 1

        ntok += 1
        if not ntok & 0xF:
            out += struct.pack("<H", flags)
            out += group
            flags = 0
            group = bytearray()

        for k in range(i, i + step):
            key = words[k]
            arr = recent.get(key)
            if arr is None:
                recent[key] = [k]
            else:
                arr.append(k)
                if len(arr) > CHAIN * 2:
                    del arr[:CHAIN]
        i += step

    if ntok & 0xF:
        out += struct.pack("<H", flags)
        out += group

    struct.pack_into("<I", out, 4, ntok)
    return out


def dg_unpack(data):
    """Return the header + decompressed data; flag at 0x57 set to 0"""
    _check(data)
    usize = struct.unpack_from("<I", data, OFS_SIZE)[0]

    if data[OFS_FLAG] == 0:
        print("Save is already unpacked, skipping")
        return data

    payload = memoryview(data)[HDR_SIZE:]
    stored = struct.unpack_from("<I", data, OFS_CSUM)[0]
    calc = xor32(payload)
    if stored != calc:
        print("Warning: checksum mismatch {:08X} != {:08X}".format(stored, calc))

    raw = _decompress(payload)
    if len(raw) != usize:
        raise Exception("Error: size mismatch {} != {}".format(len(raw), usize))

    out = bytearray(data[:HDR_SIZE])
    out[OFS_FLAG] = 0
    out += raw
    del raw
    gc.collect()

    print("Unpacked {} -> {} bytes".format(len(data), len(out)))
    return out


def dg_pack(data):
    """Recompress the data, update size, checksum and the flag at 0x57"""
    _check(data)

    if data[OFS_FLAG] != 0:
        print("Save is already packed, skipping")
        return data

    raw = memoryview(data)[HDR_SIZE:]
    payload = _compress(raw)
    gc.collect()

    out = bytearray(data[:HDR_SIZE])
    out[OFS_FLAG] = 1
    struct.pack_into("<I", out, OFS_SIZE, len(raw))
    struct.pack_into("<I", out, OFS_CSUM, xor32(payload))
    out += payload
    del payload
    gc.collect()

    print("Packed {} -> {} bytes, checksum {:08X}".format(
        len(data), len(out), struct.unpack_from("<I", out, OFS_CSUM)[0]))
    return out
