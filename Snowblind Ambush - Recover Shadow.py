#!/usr/bin/env python3
import urllib.parse
from PIL import Image, ImageFile
import io

ImageFile.LOAD_TRUNCATED_IMAGES = True

BLOCK_SIZE = 6
KNOWN_PLAINTEXT = b"root:$"

def load_png_from_sec(path="sec"):
    with open(path, "rb") as f:
        raw = f.read()

    # Case 1: percent-encoded payload
    if b"%89PNG" in raw:
        if b"secret_file=" in raw:
            raw = raw.split(b"secret_file=", 1)[1]
        return urllib.parse.unquote_to_bytes(raw.decode(errors="ignore"))

    # Case 2: already raw PNG
    if raw.startswith(b"\x89PNG"):
        return raw

    raise RuntimeError("Could not identify PNG data in sec")

def extract_encrypted_bytes(png_bytes):
    img = Image.open(io.BytesIO(png_bytes))
    pixels = img.load()

    enc = bytearray()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pixels[x, y]
            if r == 0 and g == 0:
                enc.append(b)

    return bytes(enc)

def recover_key(enc):
    return bytes(enc[i] ^ KNOWN_PLAINTEXT[i] for i in range(BLOCK_SIZE))

def decrypt(enc, key):
    pt = bytearray()
    curr_key = key

    for i in range(0, len(enc), BLOCK_SIZE):
        block = enc[i:i+BLOCK_SIZE]
        dec = bytes(block[j] ^ curr_key[j] for j in range(len(block)))
        pt += dec
        curr_key = block

    return pt.rstrip(b"\x00")

def main():
    print("[*] Loading PNG from sec")
    png_bytes = load_png_from_sec("sec")

    print("[*] Extracting encrypted data from PNG")
    enc = extract_encrypted_bytes(png_bytes)

    print("[*] Recovering XOR key")
    key = recover_key(enc)
    print(f"[+] Key recovered: {key.hex()}")

    print("[*] Decrypting /etc/shadow")
    shadow = decrypt(enc, key)

    with open("shadow.recovered", "wb") as f:
        f.write(shadow)

    print("[+] /etc/shadow recovered -> shadow.recovered")

if __name__ == "__main__":
    main()
