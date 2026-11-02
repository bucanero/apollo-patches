#
# Dead or Alive 6 (PS4) decrypter by Bucanero
# based on https://github.com/bucanero/apollo-patches/issues/33
#
# Note: the PKCS#7 padding is kept as part of the decrypted buffer, so the
# decrypted and encrypted data have the same size.
#

import gc
import ucrypto
import uhashlib

ENCRYPT = ucrypto.ENCRYPT
DECRYPT = ucrypto.DECRYPT


def derive_key_iv(name):
    """Key and IV only depend on the save file name (e.g. SYSTEMDATA)"""

    r = uhashlib.md5(name + b"\x00" * (32 - len(name)))
    hu = "".join(["%02X" % b for b in r])

    # key: uppercase hex digest, non A-F chars first, then A-F chars
    key = "".join([c for c in hu if c not in "ABCDEF"] + [c for c in hu if c in "ABCDEF"])
    # iv: digest bytes, odd values first, then even values
    iv = bytes([b for b in r if b & 1] + [b for b in r if not b & 1])

    return key.encode(), iv


def doa6_crypt(mode, data: bytearray, name=b"SYSTEMDATA"):
    """Main function to handle decryption/encryption of the save file"""

    if mode != ENCRYPT and mode != DECRYPT:
        raise Exception("Error: Unknown mode '{}', must be 'ENCRYPT' or 'DECRYPT'".format(mode))

    if len(data) == 0 or len(data) % 16:
        raise Exception("Error: Invalid data size {} (not a multiple of 16)".format(len(data)))

    key, iv = derive_key_iv(name)
    ucrypto.aes_cbc(mode, data, key, iv)

    print("{} complete, {} bytes".format("Encryption" if mode == ENCRYPT else "Decryption", len(data)))

    # Clean up
    gc.collect()
