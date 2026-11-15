#
# Samurai Warriors app.dat / DATA.BIN checksum fixer by Bucanero
# based on the fix_checksums scripts recovered from each game's eboot
#
# Every check field is a masked (& 0x7fffffff) combination of plain byte sums
# over fixed regions of the save block. Values are little-endian u32 on PS4,
# big-endian u32 on PS3.
#
#   sw4_fix()     Samurai Warriors 4 PS4      (CUSA00919)  block at 0, size 0x80536
#   sw4_ps3_fix() Samurai Warriors 4 PS3 US/JP (NPUB31564, BLJM61144, NPJB00534)
#                 DATA.BIN; JP when the dword at 0x58298 is non-zero (as apollo's
#                 BSD sw4_checksum)
#   sw4ii_fix()   Samurai Warriors 4-II        (CUSA02855/CUSA02860)  block at 0, size 0x85872
#   sos_fix()     Samurai Warriors: Spirit of Sanada (CUSA07931)
#                 0x1000 header + 4 slots of 0x28A000
#

import uhashlib
import ustruct as struct

M = 0x7FFFFFFF


def u32(v):
    return v & 0xFFFFFFFF


def _summer(data, base=0):
    mv = memoryview(data)

    def S(o, n):
        o += base
        return struct.unpack(">I", uhashlib.add(mv[o:o + n]))[0]

    return S


def _write(data, base, res, name, fmt="<I"):
    for off in sorted(res):
        old = struct.unpack_from(fmt, data, base + off)[0]
        struct.pack_into(fmt, data, base + off, res[off])
        print("{} +0x{:X}: {:08X} -> {:08X}".format(name, off, old, res[off]))


def _version(data, base=0):
    return struct.unpack_from("<I", data, base)[0]


# SW4 region bounds: (D end, F start, F end, E start, E end = last check field)
SW4_PS4 = (0x78D6, 0x78D6, 0x85FE, 0x85FE, 0x80532)
SW4_PS3_US = (0x78D6, 0x78D6, 0x85DF, 0x85DE, 0x58532)
SW4_PS3_JP = (0x7656, 0x7656, 0x835F, 0x835E, 0x58292)
SW4_PS3_JP_OFF = 0x58298


def _sw4(data, layout):
    d_end, f_start, f_end, e_start, e_end = layout

    S = _summer(data)
    A = S(0x8, 0xA0)
    B = S(0xAC, 0x840)
    C = S(0x8EC, 0x32A)
    D = S(0xC1A, d_end - 0xC1A)
    E = S(e_start, e_end - e_start)
    F = S(f_start, f_end - f_start)
    Am, Bm, Dm, Em = A & M, B & M, D & M, E & M

    r15 = u32((Dm + Am) * Bm + F)
    r10 = u32((Dm + Bm + Em) * Am)
    r12 = u32(B + A + C + D)
    fin = u32(r10 + r12 + r15)

    return {0x4: r15 & M, 0xA8: r10 & M, 0xC16: r12 & M, e_end: fin & M}


def sw4_fix(data: bytearray):
    ver = _version(data)
    if ver not in (0x18D2, 0x1CF5, 0x2118):
        raise Exception("Error: unexpected version 0x{:X}".format(ver))

    _write(data, 0, _sw4(data, SW4_PS4), "app.dat")


def sw4_ps3_fix(data: bytearray):
    if len(data) < SW4_PS3_JP_OFF + 4:
        raise Exception("Error: invalid file size {}".format(len(data)))

    jp = struct.unpack_from(">I", data, SW4_PS3_JP_OFF)[0] != 0
    print("PS3 {} save".format("JP" if jp else "US"))

    _write(data, 0, _sw4(data, SW4_PS3_JP if jp else SW4_PS3_US), "DATA.BIN", ">I")


def sw4ii_fix(data: bytearray):
    ver = _version(data)
    if ver == 0x2D81:
        raise Exception("Error: old save format 0x2D81 (load and save it in-game first)")
    if ver != 0x31A4:
        raise Exception("Error: unexpected version 0x{:X}".format(ver))

    S = _summer(data)
    A = S(0x8, 0xA0)
    B = S(0xAC, 0x960)
    C = S(0xA0C, 0x642)
    D = S(0x1052, 0xBBE4)
    E = S(0xD92E, 0x77F40)
    F = S(0xCC36, 0xCB8)
    G = S(0xD8EE, 0x40)
    Am, Bm, Dm, Em = A & M, B & M, D & M, E & M

    f4 = u32((Dm + Am) * Bm + F + G)
    fa8 = u32((Dm + Bm + Em) * Am)
    f104e = u32(B + A + C + D)
    fin = u32(fa8 + f104e + f4)

    _write(data, 0, {0x4: f4 & M, 0xA8: fa8 & M, 0x104E: f104e & M, 0x8586E: fin & M}, "app.dat")


SOS_SLOT0 = 0x1000
SOS_SLOT_SZ = 0x28A000
SOS_HB = (0x9CE34, 0xE0580, 0x123CCC, 0x167418, 0x1AAB64, 0x1EE2B0, 0x2319FC)  # 7 x 0x4374c


def _sos_slot(data, base):
    S = _summer(data, base)
    A = S(0x8, 0xA4)
    B = S(0xB0, 0x770)
    C = S(0x820, 0x7980)
    D = S(0x81A4, 0x4D0)
    E = S(0xD5BC, 0x10144)
    F = S(0x1D700, 0x7F734)
    h = [S(o, 0x4374C) for o in SOS_HB]
    Am, Bm, Em, Fm = A & M, B & M, E & M, F & M

    t1 = u32((Em + Am) * Bm)
    t2 = u32((Em + Bm + Fm) * Am)
    s3 = u32(Am + Bm + Em + C)
    s4 = u32(D + C + Am + Bm + Em)
    e5 = u32(h[5] + h[4] + h[3] + h[2] + h[1] + h[0]) & M
    s5 = u32(h[6] + e5 + A)
    s6 = u32(s3 + t1 + s4 + t2 + s5)

    return {0x4: t1 & M, 0xAC: t2 & M, 0x81A0: s3 & M, 0x8674: s4 & M,
            0x275148: s5 & M, 0x2752FC: s6 & M}


def sos_fix(data: bytearray):
    if len(data) < SOS_SLOT0 + 4 * SOS_SLOT_SZ:
        raise Exception("Error: invalid file size {}".format(len(data)))

    for k in range(4):
        base = SOS_SLOT0 + k * SOS_SLOT_SZ
        ver = _version(data, base)
        if ver not in (0x846, 0x423):
            print("Slot {}: empty (version 0x{:X}), skipped".format(k, ver))
            continue
        _write(data, base, _sos_slot(data, base), "Slot {}".format(k))
