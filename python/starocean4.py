#
# Star Ocean: The Last Hope 4K & Full HD Remaster (PS4) decrypter by Bucanero
#
# Byte-wise XOR/SUB cipher with an 8-byte key (eboot.elf @ 0xf28110):
#   decrypt: out[i] = (in[i] ^ key[i % 8]) - key[7 - i % 8]
#   encrypt: out[i] = (in[i] + key[7 - i % 8]) ^ key[i % 8]
#
# Decrypted header: u32 LE at 0x08 holds the file size, used to tell whether
# the buffer is already decrypted, so running a code twice is harmless.
#

import gc
import ustruct as struct

ENCRYPT = 1
DECRYPT = 0

KEY = b"\xe0\xba\x27\x54\x6c\x83\xad\x14"


def is_decrypted(data):
    return len(data) >= 12 and struct.unpack_from("<I", data, 8)[0] == len(data)


def _tables(mode):
    tabs = []
    for j in range(8):
        kf = KEY[j]
        kr = KEY[7 - j]
        if mode == DECRYPT:
            tabs.append(bytes([((b ^ kf) - kr) & 0xFF for b in range(256)]))
        else:
            tabs.append(bytes([((b + kr) & 0xFF) ^ kf for b in range(256)]))
    return tabs


def so4_crypt(mode, data: bytearray):
    """Decrypt/encrypt the save buffer in place"""

    if mode != ENCRYPT and mode != DECRYPT:
        raise Exception("Error: Unknown mode '{}', must be 'ENCRYPT' or 'DECRYPT'".format(mode))

    if is_decrypted(data) == (mode == DECRYPT):
        print("Save is already {}, skipping".format("decrypted" if mode == DECRYPT else "encrypted"))
        return

    tabs = _tables(mode)
    n = len(data)
    for j in range(8):
        t = tabs[j]
        for i in range(j, n, 8):
            data[i] = t[data[i]]

    print("{} complete, {} bytes".format("Encryption" if mode == ENCRYPT else "Decryption", n))

    # Clean up
    gc.collect()
