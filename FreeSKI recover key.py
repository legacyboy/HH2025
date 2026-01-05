import random, binascii

ENCODED = {
    'Mount Snow':    b"\x90\x00\x1d\xbc\x17b\xed6S\x22\xb0<Y\xd6\xce\x169\xae\xe9|\xe2Gs\xb7\xfdy\xcf5\x98",
    'Aspen':         b"U\xd7%x\xbfvj!\xfe\x9d\xb9\xc2\xd1k\x02y\x17\x9dK\x98\xf1\x92\x0f!\xf1\\\xa0\x1b\x0f",
    'Whistler':      b"\x1cN\x13\x1a\x97\xd4\xb2!\xf9\xf6\xd4#\xee\xebh\xecs.\x08M!hr9?\xde\x0c\x86\x02",
    'Mount Baker':   b"\xac\xf9#\xf4T\xf1%h\xbe3FI+h\r\x01V\xee\xc2C\x13\xf3\x97ef\xac\xe3z\x96",
    'Mount Norquay': b"\x0c\x1c\xad!\xc6,\xec0\x0b+\x22\x9f@.\xc8\x13\xadb\x86\xea{\xfeS\xe0S\x85\x90\x03q",
    'Mount Erciyes': b"n\xad\xb4l^I\xdb\xe1\xd0\x7f\x92\x92\x96\x1bq\xca`PvWg\x85\xb21^\x93F\x1a\xee",
    'Dragonmount':   b"Z\xf9\xdf\x7f_\x02\xd8\x89\x12\xd2\x11p\xb6\x96\x19\x05x))v\xc3\xecv\xf4\xe2\\\x9a\xbe\xb5",
}
HEIGHTS = {'Mount Snow':3586,'Aspen':11211,'Whistler':7156,'Mount Baker':10781,'Mount Norquay':6998,'Mount Erciyes':12848,'Dragonmount':16282}
MW = 1000

def get_treasure_locations(name, height):
    random.seed(binascii.crc32(name.encode('utf-8')))
    prev_h, prev_x = height, 0
    locs = {}
    for _ in range(5):
        e_delta = random.randint(200, 800)
        h_delta = random.randint(int(-e_delta/4), int(e_delta/4))
        prev_h -= e_delta
        prev_x += h_delta
        locs[prev_h] = prev_x
    return locs  # insertion order preserved

def setflag_decode(name):
    locs = get_treasure_locations(name, HEIGHTS[name])
    product = 0
    for e, x in locs.items():
        product = (product << 8) ^ (e*MW + (x % MW))
    rnd = random.Random(product)
    dec = bytes(b ^ rnd.randint(0,255) for b in ENCODED[name])
    return dec.decode('utf-8', errors='replace')

for m in ENCODED:
    print(m, "-> Flag:", setflag_decode(m))
